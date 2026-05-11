# -*- coding: utf-8 -*-
"""每日早报推送 - GitHub Actions 版"""

import smtplib, os, re
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup

def get_today():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    return now.strftime("%Y-%m-%d"), now.strftime("%Y年%m月%d日")

def fetch_news(url, source, domain):
    items = []
    try:
        h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=h, timeout=20)
        r.encoding = "utf-8"
        s = BeautifulSoup(r.text, "lxml")
        seen = set()
        for a in s.find_all("a", href=True):
            t = a.get_text(strip=True); u = a["href"]
            if not t or len(t) < 12 or t in seen: continue
            seen.add(t)
            if u.startswith("//"): u = "https:" + u
            elif u.startswith("/"): u = "https://" + domain + u
            elif not u.startswith("http"): u = "https://" + domain + "/" + u
            if domain not in u.lower(): continue
            items.append({"title": t.strip(), "url": u, "source": source})
    except Exception as e:
        print(f"[WARN] {source}: {e}")
    return items

def fetch_summary(url):
    try:
        h = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=h, timeout=10)
        r.encoding = "utf-8"
        s = BeautifulSoup(r.text, "lxml")
        for sel in [".content", ".article", "#content", "article", ".detail", ".main-text"]:
            el = s.select_one(sel)
            if el:
                t = re.sub(r'\s+', '', el.get_text(strip=True))
                if len(t) > 30: return t[:120] + ("…" if len(t) > 120 else "")
        for p in s.find_all("p"):
            t = re.sub(r'\s+', '', p.get_text(strip=True))
            if len(t) > 30: return t[:120] + ("…" if len(t) > 120 else "")
    except: pass
    return ""

def build_html(dc, news):
    kw = {"ai":["AI","人工智能","智能","大模型","算法","机器人","芯片","机器学习"],"tech":["航天","飞船","火箭","卫星","深海","氢能","电池","无人机","科技","新能源","量子"],"sport":["体育","比赛","冠军","奥运","世界杯","世锦赛","足球","篮球"]}
    grp = {"ai":[],"tech":[],"sport":[],"cur":[]}
    seen = set()
    for x in news:
        t = x["title"]
        if t in seen: continue
        seen.add(t)
        e = {**x, "summary": fetch_summary(x["url"])}
        matched = False
        for k, kwlist in kw.items():
            if any(kw in t for kw in kwlist): grp[k].append(e); matched = True; break
        if not matched: grp["cur"].append(e)
    for k in grp: grp[k] = grp[k][:5]
    L = ['<html><body style="font-family:Microsoft YaHei,Arial;max-width:680px;margin:0 auto;padding:20px;color:#333;background:#fafafa;">']
    L.append(f'<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:28px;border-radius:10px;text-align:center;margin-bottom:20px;"><h1 style="margin:0;font-size:24px;">📰 每日早报</h1><p style="margin:6px 0 0;opacity:.8;font-size:14px;">{dc}</p></div>')
    total = 0
    for label, key, emoji in [("AI 前沿","ai","🤖"),("今日时事","cur","🌍"),("科技探索","tech","🚀"),("体育文化","sport","⚽")]:
        if not grp[key]: continue
        L.append(f'<div style="background:#fff;border-radius:8px;padding:16px 20px;margin-bottom:14px;box-shadow:0 1px 3px rgba(0,0,0,.08);"><h2 style="font-size:16px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid #333;">{emoji} {label}</h2>')
        for x in grp[key]:
            total += 1
            L.append(f'<p style="margin:6px 0;"><a href="{x["url"]}" style="color:#333;text-decoration:none;font-size:14px;">{x["title"]}</a> <span style="color:#999;font-size:11px;">[{x["source"]}]</span></p>')
            if x["summary"]: L.append(f'<p style="color:#666;font-size:12px;margin:2px 0 8px;padding:6px 10px;background:#f5f5f5;border-radius:4px;">📝 {x["summary"]}</p>')
            else: L.append('<hr style="border:none;border-top:1px solid #eee;margin:4px 0;">')
        L.append('</div>')
    L.append(f'<div style="background:#fff;border-radius:8px;padding:16px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08);"><h2 style="font-size:16px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid #333;">🌐 一分钟看世界</h2>')
    for key, label in [("ai","AI"),("cur","国内"),("tech","科技"),("sport","体育")]:
        if grp[key]: L.append(f'<p style="margin:3px 0;font-size:13px;color:#555;">• <b>{label}</b>：{grp[key][0]["title"][:35]}{"…" if len(grp[key][0]["title"])>35 else ""}</p>')
    L.append(f'<p style="margin:6px 0 0;font-size:12px;color:#999;">共 {total} 条</p></div>')
    L.append(f'<p style="text-align:center;color:#bbb;font-size:11px;margin-top:16px;">每日早报 | {dc} | GitHub Actions 自动推送</p></body></html>')
    return "\n".join(L)

def send_email(html, subject):
    qq = os.environ.get("QQ_EMAIL",""); code = os.environ.get("QQ_AUTH_CODE","")
    if not qq or not code: print("[ERR] 缺环境变量"); return
    msg = MIMEText(html,"html","utf-8")
    msg["From"]=msg["To"]=qq; msg["Subject"]=Header(subject,"utf-8")
    try:
        s = smtplib.SMTP_SSL("smtp.qq.com",465,timeout=30)
        s.login(qq,code); s.sendmail(qq,[qq],msg.as_string()); s.quit()
        print("[OK] 成功！")
    except Exception as e: print(f"[ERR] {e}")

def main():
    d, dc = get_today()
    print(f"📰 每日早报 {d}")
    n1 = fetch_news("https://www.news.cn/","新华网","www.news.cn")[:10]
    n2 = fetch_news("https://news.cctv.cn/","央视网","news.cctv.cn")[:8]
    n3 = fetch_news("https://www.people.com.cn/","人民网","www.people.com.cn")[:6]
    all_n = n1 + n2 + n3
    if not all_n: print("[ERR] 无新闻"); return
    print(f"  {len(all_n)} 条")
    send_email(build_html(dc, all_n), f"📰 每日早报 | {d}")

if __name__ == "__main__":
    main()
