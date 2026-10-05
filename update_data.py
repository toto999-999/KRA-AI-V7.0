import os
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from collections import Counter
import time

# =========================================================================
# 프로그램 명칭: KRA전국 승부예상AI_V10.0 (전개 시나리오 & 1·2·3착 역할 매칭 엔진)
# =========================================================================
VERSION = "KRA전국 승부예상AI_V10.0"
API_KEY = os.environ.get("KRA_API_KEY", "")
URL = "http://apis.data.go.kr/B551015/racedetailresult/getracedetailresult"

KST = timezone(timedelta(hours=9))

MEET_CONFIG = [
    ("1", "서울"),
    ("4", "영천"),
    ("2", "제주"),
    ("3", "부산경남")
]

JOCKEY_RATES = {
    "문세영": 33.2, "김용근": 24.5, "빅투아르": 25.1, "유승완": 21.0,
    "송재철": 19.5, "이혁": 19.2, "임다빈": 18.5, "장추열": 18.0,
    "임기원": 17.5, "이동하": 16.0, "조인권": 21.4, "마이아": 22.0,
    "서승운": 31.5, "최시대": 26.8, "다나카": 25.4, "다비드": 24.2,
    "유현명": 23.8, "정도윤": 22.5, "김혜선": 20.8, "김동영": 17.8,
    "이성재": 16.5, "송경윤": 15.2, "전진구": 14.8, "김어수": 14.5, "손경민": 14.0,
    "전현준": 26.5, "한영민": 24.2, "임재광": 21.8, "양민재": 19.5,
    "원유일": 18.2, "박재희": 17.5, "곽용남": 16.8, "김한남": 16.0,
    "강수한": 15.5, "이동준": 15.0, "안득수": 20.5, "정명일": 19.0
}

TRAINER_RATES = {
    "서홍수": 24.5, "송문길": 21.5, "배휴준": 20.8, "정호익": 19.5,
    "최용건": 19.0, "박재우": 17.2, "이강서": 16.8, "전승규": 16.0, "서인석": 15.0,
    "김영관": 28.0, "라이스": 25.2, "민장기": 22.1, "구영준": 18.5,
    "김도현": 18.2, "안우성": 18.0, "임성실": 17.5, "백광열": 18.8, "강은석": 15.5,
    "심도연": 23.5, "김태준": 21.0, "강대은": 20.5, "김길홍": 18.5,
    "윤덕상": 17.8, "김대연": 17.2, "이준호": 16.5, "문성호": 15.8, "고성동": 22.0
}

def parse_time_seconds(time_str):
    try:
        t = str(time_str).strip().replace("'", "").replace('"', '')
        if not t: return None
        if ":" in t:
            parts = t.split(":")
            return float(parts[0]) * 60 + float(parts[1])
        if t.count(".") == 2:
            parts = t.split(".")
            return float(parts[0]) * 60 + float(f"{parts[1]}.{parts[2]}")
        val = float(t)
        if val > 20.0: return val
    except:
        pass
    return None

def clean_name(val):
    if not val: return ""
    v = re.sub(r'[\(\[\{].*?[\)\]\}]', '', str(val))
    return re.sub(r'[^가-힣a-zA-Z]', '', v).strip()

def sanitize_jockey_and_trainer(jockey, trainer, meet_name):
    jk = clean_name(jockey)
    tr = clean_name(trainer)

    if tr == "문세영":
        if jk in TRAINER_RATES:
            jk, tr = tr, jk
        else:
            tr = "관리팀"
            jk = "문세영"

    if tr in ["서승운", "김용근", "빅투아르", "유승완", "최시대", "다나카"] and jk in TRAINER_RATES:
        jk, tr = tr, jk

    return jk, tr

def fetch_meet_data(meet_code, meet_name, date_str):
    params = {
        "serviceKey": API_KEY,
        "pageNo": "1",
        "numOfRows": "180",
        "meet": meet_code,
        "rc_date": date_str
    }
    full_url = f"{URL}?{urllib.parse.urlencode(params)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "*/*"
    }

    try:
        req = urllib.request.Request(full_url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        if not items:
            return []

        print(f"[{meet_name}] API 응답 수신: {len(items)}두")

        races = {}
        for it in items:
            def gv(tag_list):
                for t in tag_list:
                    n = it.find(t)
                    if n is not None and n.text and n.text.strip():
                        return n.text.strip()
                    for child in it:
                        if child.tag.lower() == t.lower():
                            if child.text and child.text.strip():
                                return child.text.strip()
                return ""

            raw_rc_no = gv(["rcNo", "rc_no"]) or "1"
            rc_no = str(int(raw_rc_no)) if raw_rc_no.isdigit() else raw_rc_no

            raw_gate = gv(["chulNo", "chul_no", "gateNo", "hrNo"]) or "0"
            gate = str(int(raw_gate)) if raw_gate.isdigit() else raw_gate
            name = clean_name(gv(["hrName", "hr_name"]) or "경주마")

            raw_jockey = gv(["jkName", "jk_name", "jockeyName", "jockey"]) or "기수"
            raw_trainer = gv(["trName", "tr_name", "trainerName", "trainer"]) or "조교사"
            jockey, trainer = sanitize_jockey_and_trainer(raw_jockey, raw_trainer, meet_name)

            raw_dist = gv(["rcDist", "rc_dist", "distance", "dist", "rc_distance"]) or ""
            clean_dist = re.sub(r'[^0-9]', '', raw_dist)

            weight = gv(["wgBudam", "wg_budam", "weight"]) or "55.0"
            track = gv(["track", "track_state", "trackCond", "weather"]) or "양호"

            rc_time = gv(["rcTime", "rc_time", "record", "rcRecord", "ordTime"]) or ""
            past_time = gv(["bestRecord", "bestRcTime", "recentRecord", "recentRcTime", "preRcTime"]) or ""
            g1f_time = gv(["g1f", "g1f_time", "g1fTime", "g1fRecord", "g_1f"]) or ""
            win_odds = gv(["winOdds", "win_odds", "win_rate", "odds"]) or "0"
            pre_ord = gv(["preOrd", "pre_ord", "recentOrd", "preRcOrd"]) or ""

            gear_info = gv(["gear", "janggu", "hrequip", "equip", "blinker", "equipName"]) or ""
            training_info = gv(["training", "jogyo", "trackwork", "trainType", "trainRider"]) or ""
            combo_info = gv(["combo", "dongban", "jkHrRecord", "jockeyCombo"]) or ""
            
            rc_cnt = gv(["rcCnt", "rc_cnt", "totRcCnt"]) or "0"
            ord1_cnt = gv(["ord1Cnt", "ord1_cnt", "totOrd1Cnt"]) or "0"
            ord2_cnt = gv(["ord2Cnt", "ord2_cnt", "totOrd2Cnt"]) or "0"

            s1f_rank = gv(["g1p", "s1f", "g1pRank", "ord1p"]) or "99"
            is_front = True if s1f_rank in ["1", "2", "01", "02"] else False

            ord_no = "-"
            direct_ord = gv(["ordNo", "ord_no", "ord", "rc_ord", "rcOrd", "rank", "rankNo", "chaksun"])
            if direct_ord and direct_ord.isdigit() and int(direct_ord) > 0:
                ord_no = str(int(direct_ord))
            else:
                for child in it:
                    tag_low = child.tag.lower()
                    if any(ex in tag_low for ex in ["cnt", "s1f", "g1p", "g2p", "g3p", "g4p", "pass", "time"]):
                        continue
                    if any(k in tag_low for k in ["ord", "rank", "plc", "place", "chak"]):
                        txt = child.text.strip() if child.text else ""
                        if txt.isdigit() and int(txt) > 0:
                            ord_no = str(int(txt))
                            break

            key = f"{meet_name}_{rc_no}_{date_str}"
            if key not in races:
                races[key] = {
                    "meet_code": meet_code,
                    "meet_name": meet_name,
                    "race_no": rc_no,
                    "race_date": date_str,
                    "distance": clean_dist if (clean_dist and int(clean_dist) >= 800) else "1200",
                    "track": track,
                    "version": VERSION,
                    "horses": []
                }

            if clean_dist and int(clean_dist) >= 800:
                races[key]["distance"] = clean_dist

            already_exists = any(h["gate"] == gate or h["name"] == name for h in races[key]["horses"])
            if already_exists:
                continue

            races[key]["horses"].append({
                "gate": gate,
                "name": name,
                "jockey": jockey,
                "trainer": trainer,
                "weight": weight,
                "track": track,
                "rc_time": rc_time,
                "past_time": past_time,
                "g1f_time": g1f_time,
                "win_odds": win_odds,
                "pre_ord": pre_ord,
                "gear_info": gear_info,
                "training_info": training_info,
                "combo_info": combo_info,
                "rc_cnt": rc_cnt,
                "ord1_cnt": ord1_cnt,
                "ord2_cnt": ord2_cnt,
                "is_front": is_front,
                "actual_ord": ord_no,
                "horse_dist": clean_dist
            })

        # =========================================================================
        # 🎯 [V10.0 핵심] 경주 전개 시나리오 진단 및 1·2·3착 역할 매칭
        # =========================================================================
        for r in races.values():
            valid_dists = [h["horse_dist"] for h in r["horses"] if h.get("horse_dist") and int(h["horse_dist"]) >= 800]
            if valid_dists:
                dist_counts = Counter(valid_dists)
                r["distance"] = dist_counts.most_common(1)[0][0]
            dist = int(r["distance"])

            # 1. 전개 시나리오 판별
            front_runners = [h for h in r["horses"] if h["is_front"]]
            num_front = len(front_runners)

            if dist >= 1700 and num_front >= 3:
                scenario_type = "COLLAPSE" # 선행 자멸형
                r["scenario_title"] = "🔥 [선행 자멸 경합 ➔ 막판 200m 추입 역전 판도]"
                r["scenario_desc"] = "선행마 3두 이상 경합으로 결승선 200m 앞 선두권 침몰! 후미 추입마 싹쓸이 시나리오"
            elif num_front <= 1:
                scenario_type = "WIRE_TO_WIRE" # 단독 선행 독주형
                r["scenario_title"] = "⚡ [단독 선행 독주 ➔ 2선 버티기 판도]"
                r["scenario_desc"] = "경합 없는 단독 선행마의 결승선 와이어투와이어 독주 시나리오"
            else:
                scenario_type = "STANDARD"
                r["scenario_title"] = "🎯 [능력·전개 표준 경합 판도]"
                r["scenario_desc"] = "선행 2두의 안정적 페이스 유도와 직선주로 탄력 대결"

            all_weights = []
            for h in r["horses"]:
                try:
                    all_weights.append(float(re.sub(r'[^0-9.]', '', str(h["weight"]))))
                except:
                    all_weights.append(55.0)
            max_race_weight = max(all_weights) if all_weights else 55.0

            # 2. 각 말의 전개 역할 지표(Score 1착, 2착, 3착) 개별 산출
            for h in r["horses"]:
                h["distance"] = str(dist)
                tags = []
                g = int(h["gate"]) if str(h["gate"]).isdigit() else 5
                try:
                    clean_w = float(re.sub(r'[^0-9.]', '', str(h["weight"])))
                except:
                    clean_w = 55.0

                tot_rc = int(re.sub(r'[^0-9]', '', str(h.get("rc_cnt", "0"))) or 0)
                ord1_cnt = int(re.sub(r'[^0-9]', '', str(h.get("ord1_cnt", "0"))) or 0)
                ord2_cnt = int(re.sub(r'[^0-9]', '', str(h.get("ord2_cnt", "0"))) or 0)
                quinella_rate = round(((ord1_cnt + ord2_cnt) / tot_rc) * 100, 1) if tot_rc >= 3 else 20.0
                win_rate = round((ord1_cnt / tot_rc) * 100, 1) if tot_rc >= 3 else 10.0

                jk_rate = JOCKEY_RATES.get(h["jockey"], 12.0)
                tr_rate = TRAINER_RATES.get(h["trainer"], 14.0)

                if jk_rate >= 24.0: tags.append("특급 기수 🏇")
                elif jk_rate >= 19.0: tags.append("상위 기수")
                if tr_rate >= 20.0: tags.append("우수 마방 🏆")

                # 부중 및 게이트 태그
                if clean_w <= 52.5: tags.append(f"경량 부중({clean_w}kg) ⚡")
                elif clean_w >= 57.5 and clean_w == max_race_weight: tags.append("체급 최강자(탑웨이트) 🏋️")
                if dist <= 1300 and g <= 3: tags.append("단거리 황금게이트 ⚡")
                elif g >= 8 and (not h["is_front"]): tags.append("외곽 모래회피 복병 🚀")

                # 🥇 1착 적합도 점수 계산
                score_1st = 30.0 + (win_rate * 0.8) + (jk_rate * 0.4)
                if scenario_type == "WIRE_TO_WIRE" and h["is_front"]:
                    score_1st += 25.0
                    tags.append("단독선행 독주마 👑")
                elif scenario_type == "COLLAPSE":
                    if h["is_front"]:
                        score_1st -= 15.0 # 자멸 대상
                        tags.append("선행 경합 자멸주의 ⚠️")
                    else:
                        score_1st += 12.0 # 전개 이점

                # 🥈 2착 적합도 점수 계산 (선입/착순 안정성)
                score_2nd = 30.0 + (quinella_rate * 0.6) + (jk_rate * 0.3) + (tr_rate * 0.3)
                if (not h["is_front"]) and g <= 5:
                    score_2nd += 10.0

                # 🥉 3착 복병 적합도 점수 계산 (경량, 추입, 외곽 복병)
                score_3rd = 30.0
                if clean_w <= 52.5: score_3rd += 15.0
                if g >= 8: score_3rd += 12.0
                if (not h["is_front"]): score_3rd += 10.0
                if scenario_type == "COLLAPSE" and (not h["is_front"]):
                    score_3rd += 20.0
                    tags.append("중장거리 막판 추입 🚀")

                h["score_1st"] = score_1st
                h["score_2nd"] = score_2nd
                h["score_3rd"] = score_3rd
                h["ai_tags"] = tags

            # 3. 역할별 최적마 1:1 매칭
            # 🥇 1착 축마 선별
            sorted_1st = sorted(r["horses"], key=lambda x: x["score_1st"], reverse=True)
            pick_1st = sorted_1st[0]
            pick_1st["role_name"] = "1착 우승축 🥇"
            pick_1st["ai_score"] = 78.5

            # 🥈 2착 선입마 선별 (1착마 제외)
            remaining_for_2nd = [h for h in r["horses"] if h["gate"] != pick_1st["gate"]]
            sorted_2nd = sorted(remaining_for_2nd, key=lambda x: x["score_2nd"], reverse=True)
            pick_2nd = sorted_2nd[0]
            pick_2nd["role_name"] = "2착 선입마 🥈"
            pick_2nd["ai_score"] = 69.2

            # 🥉 3착 복병마 선별 (1, 2착마 제외 중 3착 복병 지수 최고마!)
            remaining_for_3rd = [h for h in remaining_for_2nd if h["gate"] != pick_2nd["gate"]]
            sorted_3rd = sorted(remaining_for_3rd, key=lambda x: x["score_3rd"], reverse=True)
            pick_3rd = sorted_3rd[0]
            pick_3rd["role_name"] = "3착 복병마 🥉"
            pick_3rd["ai_score"] = 63.8

            # 나머지 말들 점수 재조정
            remaining_others = [h for h in remaining_for_3rd if h["gate"] != pick_3rd["gate"]]
            remaining_others.sort(key=lambda x: x["score_2nd"], reverse=True)

            cur_score = 56.0
            for idx, h in enumerate(remaining_others):
                h["role_name"] = "착순권 후보" if idx < 2 else "일반 출전마"
                h["ai_score"] = round(cur_score, 1)
                cur_score = max(45.0, cur_score - 1.8)

            # 최종 정렬: 1착 우승축 ➔ 2착 선입 ➔ 3착 복병 ➔ 나머지
            r["horses"] = [pick_1st, pick_2nd, pick_3rd] + remaining_others

            # 삼복승/복연승 추천 조건
            r["is_trio_target"] = (scenario_type == "COLLAPSE" or dist <= 1200)
            r["trio_reason"] = r["scenario_title"]

        return list(races.values())

    except Exception as e:
        print(f"[{meet_name}] 통신 에러: {e}")
        return []

def sync_5weeks_archive():
    now = datetime.now(KST)
    existing_races = {}
    if os.path.exists("race_data.json"):
        try:
            with open("race_data.json", "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for r in old_list:
                    k = f"{r.get('race_date')}_{r.get('meet_name')}_{r.get('race_no')}"
                    existing_races[k] = r
            print(f"📦 기존 아카이브에서 {len(existing_races)}개 경주 로드 완료")
        except Exception:
            existing_races = {}

    dates_to_fetch = [
        (now - timedelta(days=1)).strftime("%Y%m%d"),
        now.strftime("%Y%m%d"),
        (now + timedelta(days=1)).strftime("%Y%m%d")
    ]

    print(f"🔄 최신 정밀 데이터 수집: {dates_to_fetch}")
    for dt in dates_to_fetch:
        for m_code, m_name in MEET_CONFIG:
            res = fetch_meet_data(m_code, m_name, dt)
            for r in res:
                k = f"{r.get('race_date')}_{r.get('meet_name')}_{r.get('race_no')}"
                existing_races[k] = r

    cutoff_date = (now - timedelta(days=35)).strftime("%Y%m%d")
    final_list = [r for k, r in existing_races.items() if str(r.get("race_date", "")) >= cutoff_date]
    return final_list

def main():
    if not API_KEY:
        print("❌ KRA_API_KEY 미설정")
        return

    all_races = sync_5weeks_archive()

    if all_races:
        meet_order = {"서울": 1, "부산경남": 2, "영천": 3, "제주": 4}
        all_races.sort(key=lambda x: (
            x["race_date"],
            meet_order.get(x["meet_name"], 9),
            int(x["race_no"]) if str(x["race_no"]).isdigit() else 99
        ))
        with open("race_data.json", "w", encoding="utf-8") as f:
            json.dump(all_races, f, ensure_ascii=False, indent=2)
        print(f"🎉 성공: [{VERSION}] 전개 시나리오 & 1·2·3착 역할 매칭 갱신 완료! (총 {len(all_races)}개 경주)")
    else:
        print("❌ 데이터를 가져오지 못했습니다.")

if __name__ == "__main__":
    main()
