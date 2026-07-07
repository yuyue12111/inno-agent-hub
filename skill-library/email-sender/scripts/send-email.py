#!/usr/bin/env python3
"""email-sender —— 可移植的邮件发送技能脚本。

设计目标：作为一个自包含 skill 分发。装了 skill 后，配置一次即可让
agent 具备真正发送邮件的能力。与任何具体工作区解耦。

配置来源（读取优先级：高 -> 低）：
  1. 环境变量 SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM / SMTP_TLS
  2. 环境变量 INNO_EMAIL_CONFIG 指定的 json 路径
  3. 家目录配置：$INNO_HOME/email.json（默认 ~/.inno-agent/email.json）

发送日志：默认写到 <配置目录>/email-send-log.md，可用 INNO_EMAIL_LOG 覆盖。

子命令：
  send            撰写并发送（默认 dry-run；加 --send 才真正发送）
  config set      写入/更新配置（支持 --provider 自动填 host/port/tls）
  config show     脱敏查看当前配置
  config path     打印配置文件路径
  check           自检配置是否完整；加 --test 尝试登录 SMTP（不发信）

用法示例：
  # 1) 引导配置（163 邮箱，密码填“客户端授权码”）
  python send-email.py config set --provider 163 \
      --user teacher@163.com --password <授权码>

  # 2) 自检 + 连通性测试
  python send-email.py check --test

  # 3) 预览（默认，安全，不发信）
  python send-email.py send --to a@x.com,b@y.com --subject "调课通知" --body-file notice.txt

  # 4) 确认后真正发送
  python send-email.py send --to a@x.com,b@y.com --subject "调课通知" --body-file notice.txt --send
"""
import argparse
import json
import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr, formatdate
from pathlib import Path

# 常见邮箱服务商预设：省去用户记 host/port/tls。
PROVIDERS = {
    "163":     {"host": "smtp.163.com",        "port": 465, "tls": "ssl"},
    "126":     {"host": "smtp.126.com",        "port": 465, "tls": "ssl"},
    "qq":      {"host": "smtp.qq.com",         "port": 465, "tls": "ssl"},
    "exmail":  {"host": "smtp.exmail.qq.com",  "port": 465, "tls": "ssl"},   # 腾讯企业邮
    "aliyun":  {"host": "smtp.aliyun.com",     "port": 465, "tls": "ssl"},
    "feishu":  {"host": "smtp.feishu.cn",      "port": 465, "tls": "ssl"},   # 飞书邮箱
    "gmail":   {"host": "smtp.gmail.com",      "port": 465, "tls": "ssl"},
    "outlook": {"host": "smtp.office365.com",  "port": 587, "tls": "starttls"},
}

# 各服务商拿“授权码/应用专用密码”的提示。
AUTHCODE_HINT = {
    "163": "网页登录 163 邮箱 → 设置 → POP3/SMTP/IMAP → 开启服务 → 生成授权码（非登录密码）",
    "126": "网页登录 126 邮箱 → 设置 → POP3/SMTP/IMAP → 开启服务 → 生成授权码（非登录密码）",
    "qq": "网页登录 QQ 邮箱 → 设置 → 账户 → 开启 SMTP → 生成授权码（非登录密码）",
    "exmail": "使用邮箱登录密码，或在管理后台开启客户端专用密码",
    "gmail": "开启两步验证后，在 Google 账户 → 安全 → 应用专用密码 生成 16 位密码",
    "outlook": "使用账户密码；若开启两步验证则需生成应用密码",
}

REQUIRED = ["host", "port", "user", "password", "from"]


def home_dir() -> Path:
    return Path(os.environ.get("INNO_HOME", str(Path.home() / ".inno-agent"))).expanduser()


def config_path() -> Path:
    if os.environ.get("INNO_EMAIL_CONFIG"):
        return Path(os.environ["INNO_EMAIL_CONFIG"]).expanduser()
    return home_dir() / "email.json"


def log_path() -> Path:
    if os.environ.get("INNO_EMAIL_LOG"):
        return Path(os.environ["INNO_EMAIL_LOG"]).expanduser()
    return config_path().parent / "email-send-log.md"


def load_file_config() -> dict:
    p = config_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            sys.exit(f"[错误] 配置文件解析失败 {p}: {e}")
    return {}


def load_config() -> dict:
    """合并文件配置与环境变量，环境变量优先。"""
    cfg = load_file_config()
    env_map = {
        "host": "SMTP_HOST", "port": "SMTP_PORT", "user": "SMTP_USER",
        "password": "SMTP_PASS", "from": "SMTP_FROM", "tls": "SMTP_TLS",
    }
    for key, env in env_map.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg.setdefault("from", cfg.get("user", ""))
    cfg.setdefault("tls", "ssl")
    if cfg.get("port"):
        cfg["port"] = int(cfg["port"])
    return cfg


def mask(secret: str) -> str:
    if not secret:
        return "(空)"
    if len(secret) <= 4:
        return "****"
    return secret[:2] + "*" * (len(secret) - 4) + secret[-2:]


def missing_fields(cfg: dict) -> list[str]:
    return [k for k in REQUIRED if not cfg.get(k)]


# ---------------- config 子命令 ----------------

def cmd_config_set(args):
    cfg = load_file_config()
    if args.provider:
        key = args.provider.lower()
        if key not in PROVIDERS:
            sys.exit(f"[错误] 未知服务商 '{args.provider}'。可选：{', '.join(PROVIDERS)}")
        cfg.update(PROVIDERS[key])
    for field in ("host", "user", "password", "from", "tls"):
        val = getattr(args, field.replace("-", "_"), None)
        if val is not None:
            cfg[field] = val
    if args.port is not None:
        cfg["port"] = args.port
    cfg.setdefault("from", cfg.get("user", ""))
    cfg.setdefault("tls", "ssl")

    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(p, 0o600)  # 保护凭据，仅本人可读写
    except OSError:
        pass
    print(f"[已保存] 配置写入 {p}（权限 600）")
    miss = missing_fields(load_config())
    if miss:
        print(f"[提示] 仍缺少字段：{', '.join(miss)}")
    else:
        print("[提示] 配置已完整。可运行 `check --test` 验证登录，或直接 send 预览。")


def cmd_config_show(args):
    p = config_path()
    if not p.exists() and not any(os.environ.get(e) for e in ("SMTP_HOST", "SMTP_USER")):
        print(f"[未配置] 配置文件不存在：{p}")
        print("运行 `config set --provider <163/qq/gmail...> --user <邮箱> --password <授权码>` 完成配置。")
        return
    cfg = load_config()
    print(f"配置文件 : {p}{'（存在）' if p.exists() else '（不存在，来自环境变量）'}")
    print(f"host     : {cfg.get('host', '(未设置)')}")
    print(f"port     : {cfg.get('port', '(未设置)')}")
    print(f"tls      : {cfg.get('tls', '(未设置)')}")
    print(f"user     : {cfg.get('user', '(未设置)')}")
    print(f"from     : {cfg.get('from', '(未设置)')}")
    print(f"password : {mask(cfg.get('password', ''))}")
    miss = missing_fields(cfg)
    print(f"状态     : {'✅ 完整' if not miss else '⚠️ 缺少 ' + ', '.join(miss)}")


def cmd_config_path(args):
    print(config_path())


# ---------------- check 子命令 ----------------

def cmd_check(args):
    cfg = load_config()
    miss = missing_fields(cfg)
    print(f"配置文件 : {config_path()}")
    if miss:
        print(f"结果     : ⚠️ 配置不完整，缺少 {', '.join(miss)}")
        print("请运行 config set 补全。示例：")
        print("  python send-email.py config set --provider 163 --user you@163.com --password <授权码>")
        sys.exit(1)
    print("结果     : ✅ 配置完整")
    if not args.test:
        print("（加 --test 可尝试登录 SMTP 验证账号/授权码是否正确，不会发信）")
        return
    print("正在测试 SMTP 登录（不发信）…")
    try:
        server = _connect(cfg)
        with server:
            server.login(cfg["user"], cfg["password"])
        print("登录     : ✅ 成功，账号与授权码有效")
    except Exception as e:  # noqa: BLE001
        print(f"登录     : ❌ 失败 —— {type(e).__name__}: {e}")
        _login_hint(cfg)
        sys.exit(1)


def _login_hint(cfg):
    guess = None
    host = cfg.get("host", "")
    for k, v in PROVIDERS.items():
        if v["host"] == host:
            guess = k
            break
    if guess and guess in AUTHCODE_HINT:
        print(f"[提示] {guess} 获取授权码：{AUTHCODE_HINT[guess]}")
    print("[提示] 多数邮箱 SMTP 登录需要“客户端授权码/应用专用密码”，不是网页登录密码。")


# ---------------- send 子命令 ----------------

def _connect(cfg):
    tls = str(cfg.get("tls", "ssl")).lower()
    host, port = cfg["host"], int(cfg["port"])
    if tls == "ssl":
        return smtplib.SMTP_SSL(host, port, timeout=30)
    server = smtplib.SMTP(host, port, timeout=30)
    if tls == "starttls":
        server.starttls()
    return server


def parse_recipients(raw: str) -> list[str]:
    parts = [p.strip() for chunk in raw.split(",") for p in chunk.split(";")]
    return [p for p in parts if p]


def read_body(args) -> str:
    if args.body_file:
        return Path(args.body_file).read_text(encoding="utf-8")
    if args.body:
        return args.body
    if not sys.stdin.isatty():
        return sys.stdin.read()
    sys.exit("[错误] 未提供正文，请用 --body / --body-file 或标准输入。")


def print_preview(cfg, recipients, subject, body, will_send):
    line = "=" * 60
    print(line)
    print("邮件预览" + ("（真实发送模式）" if will_send else "（DRY-RUN：不会真正发送）"))
    print(line)
    print(f"发件人 : {cfg.get('from') or '(未配置)'}")
    print(f"收件人 : {len(recipients)} 人 -> {', '.join(recipients)}")
    print(f"主  题 : {subject}")
    print(f"SMTP   : {cfg.get('host', '(未配置)')}:{cfg.get('port', '?')} tls={cfg.get('tls')}")
    print("-" * 60)
    print(body)
    print(line)


def append_log(recipients, subject, status):
    p = log_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text(
            "# 邮件发送日志\n\n"
            "| 时间 | 主题 | 收件人数 | 收件人 | 状态 |\n"
            "|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"| {ts} | {subject} | {len(recipients)} | {', '.join(recipients)} | {status} |\n")


def cmd_send(args):
    cfg = load_config()
    recipients = parse_recipients(args.to)
    if not recipients:
        sys.exit("[错误] 收件人为空。")
    body = read_body(args)

    print_preview(cfg, recipients, args.subject, body, args.send)

    if not args.send:
        print("\n[DRY-RUN] 未发送。确认无误后加 --send 真正发送。")
        return

    miss = missing_fields(cfg)
    if miss:
        sys.exit(f"[错误] SMTP 配置缺失：{', '.join(miss)}。请先运行 config set 完成配置。")

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(args.subject, "utf-8")
    msg["From"] = formataddr((str(Header(args.from_name or "", "utf-8")), cfg["from"]))
    msg["To"] = ", ".join(recipients)
    msg["Date"] = formatdate(localtime=True)
    try:
        server = _connect(cfg)
        with server:
            server.login(cfg["user"], cfg["password"])
            server.sendmail(cfg["from"], recipients, msg.as_string())
    except Exception as e:  # noqa: BLE001
        append_log(recipients, args.subject, f"❌ 失败({type(e).__name__})")
        _login_hint(cfg)
        sys.exit(f"[发送失败] {type(e).__name__}: {e}")

    append_log(recipients, args.subject, "✅ 成功")
    print(f"\n[已发送] {len(recipients)} 封，已记录到 {log_path()}")


def build_parser():
    ap = argparse.ArgumentParser(prog="send-email.py", description="可移植邮件发送技能")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("send", help="撰写并发送（默认 dry-run）")
    s.add_argument("--to", required=True, help="收件人，逗号/分号分隔")
    s.add_argument("--subject", required=True)
    s.add_argument("--body")
    s.add_argument("--body-file")
    s.add_argument("--from-name", help="发件人显示名（可选）")
    s.add_argument("--send", action="store_true", help="真正发送")
    s.set_defaults(func=cmd_send)

    c = sub.add_parser("config", help="管理 SMTP 配置")
    csub = c.add_subparsers(dest="subcmd", required=True)
    cs = csub.add_parser("set", help="写入/更新配置")
    cs.add_argument("--provider", help=f"服务商预设：{', '.join(PROVIDERS)}")
    cs.add_argument("--host")
    cs.add_argument("--port", type=int)
    cs.add_argument("--user")
    cs.add_argument("--password", help="客户端授权码/应用专用密码")
    cs.add_argument("--from", dest="from", help="发件地址，默认同 user")
    cs.add_argument("--tls", choices=["ssl", "starttls", "none"])
    cs.set_defaults(func=cmd_config_set)
    csub.add_parser("show", help="脱敏查看配置").set_defaults(func=cmd_config_show)
    csub.add_parser("path", help="打印配置路径").set_defaults(func=cmd_config_path)

    ck = sub.add_parser("check", help="自检配置")
    ck.add_argument("--test", action="store_true", help="尝试登录 SMTP（不发信）")
    ck.set_defaults(func=cmd_check)
    return ap


def main():
    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
