# -*- coding: utf-8 -*-
"""每日早报推送脚本"""

import smtplib
import os
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime
import requests
from bs4 import BeautifulSoup


def get_today():
    now = datetime.now()
    return now.strftime("%Y-%m-%d"), now.strftime("%Y年%m月%d日")


def fetch_xinhua_news():
    news = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://www.news.cn/", headers=headers, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            href = link["href"]
            if title and len(title) > 10 and not href.startswith("#"):
                if not href.startswith("http"):
                    href = "https://www.news.cn" + href
                news.append({"title": title, "url": href, "source": "新华网"})
    except Exception as e:
        print(f"Failed: {e}")
    return news[:15]


def fetch_cctv_news():
    news = []
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://news.cctv.cn/", headers=headers, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")
        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            href = link["href"]
            if title and len(title) > 8 and "cctv" in href.lower():
                if not href.startswith("http"):
                    href = "https://news.cctv.cn" + href
                news.append({"title": title, "url": href, "source": "央视网"})
    except Exception as e:
        print(f"Failed: {e}")
    return news[:10]


def build_html(date_str, date_cn, xinhua_news, cctv_news):
    ai_kw = ["AI", "人工智能", "智能", "大模型", "算法", "数据", "机器人", "芯片"]
    tech_kw = ["航天", "飞船", "火箭", "卫星", "深海", "氢能", "电池", "无人机", "科技", "新能源"]
    sport_kw = ["体育", "比赛", "冠军", "奥运", "世界杯", "世锦赛", "乒", "足球", "篮球"]
    ai_news, tech_news, cur_news, sport_news = [], [], [], []
    for item in xinhua_news + cctv_news:
        t = item["title"]
        if any(k in t for k in ai_kw): ai_news.append(item)
        elif any(k in t for k in tech_kw): tech_news.append(item)
        elif any(k in t for k in sport_kw): sport_news.append(item)
        else: cur_news.append(item)
    def dedup(items):
        seen = set(); r = []
        for x in items:
            if x["title"] not in seen: seen.add(x["title"]); r.append(x)
        return r
    ai_news = dedup(ai_news)[:4]; tech_news = dedup(tech_news)[:3]
    cur_news = dedup(cur_news)[:5]; sport_news = dedup(sport_news)[:2]
    lines = ['<html><body style="font-family:Microsoft YaHei,Arial;max-width:680px;margin:0 auto;padding:20px;color:#333;">']
    lines.append('<h2 style="border-bottom:2px solid #333;padding-bottom:8px;">AI 前沿</h2><hr style="border:1px solid #ddd;margin:14px 0;">')
    for item in ai_news[:3]:
        lines.append(f'<p style="margin:18px 0 6px;font-size:15px;font-weight:bold;"> {item["title"]}</p>')
        lines.append(f'<p style="margin:6px 0;color:#888;font-size:13px;">来源：<a href="{item["url"]}">{item["source"]}</a></p><br>')
    lines.append('<h2 style="border-bottom:2px solid #333;padding-bottom:8px;">今日时事</h2><hr style="border:1px solid #ddd;margin:14px 0;">')
    for item in cur_news[:4]:
        lines.append(f'<p style="margin:18px 0 6px;font-size:15px;font-weight:bold;"> {item["title"]}</p>')
        lines.append(f'<p style="margin:6px 0;color:#888;font-size:13px;">来源：<a href="{item["url"]}">{item["source"]}</a></p><br>')
    if tech_news:
        lines.append('<h2 style="border-bottom:2px solid #333;padding-bottom:8px;">科技探索</h2><hr style="border:1px solid #ddd;margin:14px 0;">')
        for item in tech_news[:2]:
            lines.append(f'<p style="margin:18px 0 6px;font-size:15px;font-weight:bold;"> {item["title"]}</p>')
            lines.append(f'<p style="margin:6px 0;color:#888;font-size:13px;">来源：<a href="{item["url"]}">{item["source"]}</a></p><br>')
    lines.append('<h2 style="border-bottom:2px solid #333;padding-bottom:8px;">一分钟看世界</h2><hr style="border:1px solid #ddd;margin:14px 0;">')
    total = len(xinhua_news) + len(cctv_news)
    lines.append(f'<p><b>国内</b>：新华网今日要闻 {len(xinhua_news)} 条</p>')
    lines.append(f'<p><b>科技</b>：AI、航天等 {len(tech_news)} 条</p>')
    lines.append(f'<p><b>更多</b>：共收录 {total} 条新闻</p>')
    lines.append('<br><hr style="border:1px solid #eee;"><p style="color:#999;font-size:12px;text-align:center;">- end -</p></body></html>')
    return "\n".join(lines)


def send_email(html_content, subject):
    qq_email = os.environ.get("QQ_EMAIL", "")
    auth_code = os.environ.get("QQ_AUTH_CODE", "")
    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = f"Daily News <{qq_email}>"
    msg["To"] = qq_email
    msg["Subject"] = Header(subject, "utf-8")
    server = smtplib.SMTP_SSL("smtp.qq.com", 465)
    server.login(qq_email, auth_code)
    server.sendmail(qq_email, [qq_email], msg.as_string())
    server.quit()
    print("OK!")


def main():
    date_str, date_cn = get_today()
    print(f"Daily News {date_str}")
    xn = fetch_xinhua_news()
    ct = fetch_cctv_news()
    html = build_html(date_str, date_cn, xn, ct)
    send_email(html, f"每日早报 | {date_str}")


if __name__ == "__main__":
    main()
