# -*- coding: utf-8 -*-
"""每日早报 - GitHub Actions 推送"""

import smtplib, os, re
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta
import requests
from bs4 import BeautifulSoup


def today():
    tz = timezone(timedelta(hours=8))
    n = datetime.now(tz)
    w = ["星期一","星期二","星期三","星期四","星期五","星期六","星期日"]
    return n.strftime("%Y-%m-%d"), f"{n.strftime('%Y年%m月%d日')} {w[n.weekday()]}"


def get_news(url, source, limit=8):
    """从新闻网站抓取文章列表，过滤导航链接"""
    items = []
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=h, timeout=20)
        r.encoding = "utf-8"
        s = BeautifulSoup(r.text, "lxml")
        nav_words = ["русский", "english", "日本語", "한국어", "注册", "登录", "设为首页", "加入收藏",
                     "关于", "联系", "版权", "隐私", "广告", "投稿", "网站地图", "帮助", "客户端",
                     "微博", "微信", "邮箱", "导航", "首页", "滚动", "要闻", "直播"]
        skip_domains = ["blog.", "wiki.", "bbs.", "forum.", "mall.", "shop."]
        seen = set()
        for a in s.find_all("a", href=True):
            t = a.get_text(strip=True)
            u = a["href"]
            if not t or len(t) < 15:
                continue
            # 过滤导航词
            if any(w in t.lower() for w in nav_words):
                continue
            if t in seen:
                continue
            seen.add(t)
            # 补齐 URL
            if u.startswith("//"): u = "https:" + u
            elif u.startswith("/"): u = "https://" + re.sub(r'https?://', '', url).split('/')[0] + u
            elif not u.startswith("http"): continue
            # 跳过垃圾域名
            if any(d in u.lower() for d in skip_domains): continue
            items.append({"title": t, "url": u, "src": source})
            if len(items) >= limit: break
    except Exception as e:
        print(f"  [WARN] {source}: {e}")
    return items


def get_psych_news():
    """获取心理相关文章"""
    items = []
    sources = [
        ("https://www.xinhuanet.com/health/", "新华网健康"),
        ("https://health.people.com.cn/", "人民网健康"),
    ]
    kw = ["心理", "情绪", "压力", "焦虑", "睡眠", "抑郁", "幸福", "社交", "自信", "习惯", "沟通", "成长"]
    for url, src in sources:
        try:
            h = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=h, timeout=15)
            r.encoding = "utf-8"
            s = BeautifulSoup(r.text, "lxml")
            for a in s.find_all("a", href=True):
                t = a.get_text(strip=True)
                if len(t) > 12 and any(k in t for k in kw):
                    u = a["href"]
                    if not u.startswith("http"): u = "https://www.xinhuanet.com" + u if u.startswith("/") else "https://www.xinhuanet.com/" + u
                    items.append({"title": t, "url": u, "src": src})
                    if len(items) >= 4: break
        except: pass
    return items


def get_summary(url):
    try:
        h = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=h, timeout=8)
        r.encoding = "utf-8"
        s = BeautifulSoup(r.text, "lxml")
        for sel in [".content", ".article", "#content", "article", ".detail", ".text", ".main-text"]:
            el = s.select_one(sel)
            if el:
                t = re.sub(r'\s+', '', el.get_text(strip=True))
                if len(t) > 40: return t[:150] + ("…" if len(t) > 150 else "")
        for p in s.find_all("p"):
            t = re.sub(r'\s+', '', p.get_text(strip=True))
            if len(t) > 40: return t[:150] + ("…" if len(t) > 150 else "")
    except: pass
    return ""


def classify(title):
    kw_ai = ["AI","人工智能","智能","大模型","算法","机器人","芯片","机器学习","自动驾驶","GPT"]
    kw_tech = ["航天","飞船","火箭","卫星","深海","氢能","电池","无人机","新能源","量子","5G","6G"]
    kw_sport = ["体育","比赛","冠军","奥运","世界杯","足球","篮球","网球","金牌","亚运","世锦赛"]
    if any(k in title for k in kw_ai): return "ai"
    if any(k in title for k in kw_tech): return "tech"
    if any(k in title for k in kw_sport): return "sport"
    return "news"


plain_talk = {
    "大模型":"超大AI大脑，读了几千亿字学会写东西答问题",
    "人工智能":"让电脑像人一样思考和学习的科技",
    "AI":"人工智能缩写",
    "算法":"教电脑解题的步骤指令",
    "芯片":"指甲盖大小的电脑大脑",
    "机器学习":"让电脑自己从数据学规律",
    "机器人":"能自动执行任务的机器",
    "自动驾驶":"车子自己看路自己开",
    "量子":"利用原子规律的超快计算机",
    "5G":"第五代移动网络，比4G快10倍",
    "氢能":"烧完只排水的清洁燃料",
    "新能源":"太阳能风能等不枯竭能源",
}


def build_html(dc, news, psych):
    grp = {"ai":[],"tech":[],"sport":[],"news":[]}
    seen = set()
    for x in news:
        t = x["title"]
        if t in seen: continue
        seen.add(t)
        cat = classify(t)
        e = {**x, "summary": get_summary(x["url"])}
        grp[cat].append(e)
    for k in grp: grp[k] = grp[k][:5]

    total = 0
    L = ['<html><body style="font-family:Microsoft YaHei,Arial,sans-serif;max-width:680px;margin:0 auto;padding:20px;color:#333;background:#f5f5f5;">']
    L.append(f'<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:28px 24px;border-radius:12px;text-align:center;margin-bottom:20px;"><h1 style="margin:0;font-size:24px;">📰 每日早报</h1><p style="margin:8px 0 0;opacity:.8;font-size:13px;">{dc}</p></div>')

    secs = [("🤖 AI 前沿","ai",""),("🧠 心理驿站","psych",""),("🌍 今日时事","news",""),("🚀 科技探索","tech",""),("⚽ 体育文化","sport","")]
    for title, key, _ in secs:
        items = psych if key == "psych" else grp.get(key,[])
        if not items: continue
        L.append(f'<div style="background:#fff;border-radius:10px;padding:16px 20px;margin-bottom:16px;box-shadow:0 1px 4px rgba(0,0,0,.06);">')
        L.append(f'<h2 style="font-size:16px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid #333;">{title}</h2>')
        for it in items[:4]:
            total += 1
            L.append(f'<div style="margin-bottom:8px;padding:8px 10px;background:#fafafa;border-radius:6px;border-left:3px solid #ddd;">')
            L.append(f'<p style="margin:0;"><a href="{it["url"]}" style="color:#222;text-decoration:none;font-size:13px;font-weight:bold;">{it["title"]}</a> <span style="color:#999;font-size:11px;">[{it["src"]}]</span></p>')
            # AI 大白话
            if key == "ai":
                for kw, exp in plain_talk.items():
                    if kw in it["title"]:
                        L.append(f'<p style="margin:3px 0 0;color:#2a6496;font-size:12px;padding:3px 6px;background:#e8f0fe;border-radius:3px;">💡 {kw}：{exp}</p>')
                        break
            if it.get("summary"):
                L.append(f'<p style="color:#555;font-size:12px;margin:3px 0 0;">{it["summary"]}</p>')
            L.append('</div>')
        L.append('</div>')

    # 一分钟看世界
    L.append(f'<div style="background:#fff;border-radius:10px;padding:16px 20px;box-shadow:0 1px 4px rgba(0,0,0,.06);">')
    L.append(f'<h2 style="font-size:16px;margin:0 0 10px;padding-bottom:6px;border-bottom:2px solid #333;">🌐 一分钟看世界</h2>')
    for k, lb in [("ai","AI"),("news","国内"),("tech","科技"),("sport","体育")]:
        if grp[k]:
            t = grp[k][0]["title"]
            L.append(f'<p style="margin:4px 0;font-size:13px;color:#444;">• <b style="color:#1a1a2e;">{lb}</b>：{t[:45]}{"…" if len(t)>45 else ""}</p>')
    if psych:
        L.append(f'<p style="margin:4px 0;font-size:13px;color:#444;">• <b style="color:#1a1a2e;">心理</b>：{psych[0]["title"][:45]}{"…" if len(psych[0]["title"])>45 else ""}</p>')
    L.append(f'<p style="margin:8px 0 0;font-size:11px;color:#aaa;border-top:1px solid #eee;padding-top:6px;">共 {total} 条 · 新华网/央视网/人民网</p></div>')
    L.append(f'<p style="text-align:center;color:#bbb;font-size:11px;margin-top:16px;">每日早报 | {dc} | 自动推送</p></body></html>')
    return "\n".join(L)


def send_email(html, subj):
    qq = os.environ.get("QQ_EMAIL","")
    code = os.environ.get("QQ_AUTH_CODE","")
    if not qq or not code: print("[ERR] 缺环境变量"); return
    m = MIMEText(html,"html","utf-8")
    m["From"] = f"每日早报 <{qq}>"
    m["To"] = qq
    m["Subject"] = Header(subj,"utf-8")
    try:
        s = smtplib.SMTP_SSL("smtp.qq.com",465,timeout=30)
        s.login(qq,code); s.sendmail(qq,[qq],m.as_string()); s.quit()
        print("[OK] 发送成功")
    except Exception as e: print(f"[ERR] {e}")


def main():
    d, dc = today()
    print(f"📰 每日早报 {d}")
    print("="*30)
    n1 = get_news("https://www.news.cn/","新华网",10)
    n2 = get_news("https://news.cctv.cn/","央视网",8)
    n3 = get_news("https://www.people.com.cn/","人民网",6)
    psych = get_psych_news()
    print(f"  新华网:{len(n1)} 央视网:{len(n2)} 人民网:{len(n3)} 心理:{len(psych)}")
    all_n = n1+n2+n3
    if not all_n: print("[ERR] 无新闻"); return
    print(f"  共 {len(all_n)} 条 + 心理 {len(psych)} 条")
    send_email(build_html(dc, all_n, psych), f"📰 每日早报 | {d}")
    print("="*30)
    print("✅ 完成")

if __name__ == "__main__":
    main()

