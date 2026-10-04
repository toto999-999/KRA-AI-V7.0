import os
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import time

# =========================================================================
# 프로그램 명칭: KRA전국 승부예상AI_V8.8 (5주치 누적 빅데이터 아카이브 엔진)
# =========================================================================
VERSION = "KRA전국 승부예상AI_V8.8"
API_KEY = os.environ.get("KRA_API_KEY", "")
URL = "http://apis.data.go.kr/B551015/racedetailresult/getracedetailresult"

KST = timezone(timedelta(hours=9))

MEET_CONFIG = [
    ("1", "서울"),
    ("4", "영천"),
    ("2", "제주"),
    ("3", "부산경남")
]

# 🎯 마사회 공식 편성표 1:1 전수 매핑 테이블 (황금연휴 공식 거리)
EXACT_RACE_DISTANCES = {
    # 10월 2일 (금)
    ("20261002", "부산경남", "1"): "1000", ("20261002", "부산경남", "2"): "1000",
    ("20261002", "부산경남", "3"): "1200", ("20261002", "부산경남", "4"): "1400",
    ("20261002", "부산경남", "5"): "1300", ("20261002", "부산경남", "6"): "1300",
    ("20261002", "부산경남", "7"): "1600", ("20261002", "부산경남", "8"): "1800", ("20261002", "부산경남", "9"): "1800",
    ("20261002", "제주", "1"): "900",  ("20261002", "제주", "2"): "1000",
    ("20261002", "제주", "3"): "1000", ("20261002", "제주", "4"): "1000",
    ("20261002", "제주", "5"): "1110", ("20261002", "제주", "6"): "1200", ("20261002", "제주", "7"): "1400",

    # 10월 3일 (토)
    ("20261003", "서울", "1"): "1000", ("20261003", "서울", "2"): "1200",
    ("20261003", "서울", "3"): "1400", ("20261003", "서울", "4"): "1300",
    ("20261003", "서울", "5"): "1200", ("20261003", "서울", "6"): "1700",
    ("20261003", "서울", "7"): "1800", ("20261003", "서울", "8"): "1600",
    ("20261003", "서울", "9"): "1300", ("20261003", "서울", "10"): "1200",
    ("20261003", "제주", "1"): "900",  ("20261003", "제주", "2"): "900",
    ("20261003", "제주", "3"): "1000", ("20261003", "제주", "4"): "1110",
    ("20261003", "제주", "5"): "1110", ("20261003", "제주", "6"): "1200", ("20261003", "제주", "7"): "1300",

    # 10월 4일 (일) 오늘!
    ("20261004", "영천", "1"): "1200", ("20261004", "영천", "2"): "1400",
    ("20261004", "영천", "3"): "1400", ("20261004", "영천", "4"): "1800",
    ("20261004", "영천", "5"): "1200", ("20261004", "영천", "6"): "1200",
    ("20261004", "서울", "1"): "1000", ("20261004", "서울", "2"): "1300",
    ("20261004", "서울", "3"): "1700", ("20261004", "서울", "4"): "1200",
    ("20261004", "서울", "5"): "1200", ("20261004", "서울", "6"): "1400",
    ("20261004", "서울", "7"): "1800", ("20261004", "서울", "8"): "2000",
    ("20261004", "서울", "9"): "1200", ("20261004", "서울", "10"): "1400", ("20261004", "서울", "11"): "1200",

    # 10월 5일 (월 대체공휴일)
    ("20261005", "서울", "1"): "1000", ("20261005", "서울", "2"): "1300",
    ("20261005", "서울", "3"): "1200", ("20261005", "서울", "4"): "1400",
    ("20261005", "서울", "5"): "1400", ("20261005", "서울", "6"): "1200",
    ("20261005", "서울", "7"): "1700", ("20261005", "서울", "8"): "1800",
    ("20261005", "서울", "9"): "1400", ("20261005", "서울", "10"): "1200",
    ("20261005", "제주", "1"): "900",  ("20261005", "제주", "2"): "1000",
    ("20261005", "제주", "3"): "1000", ("20261005", "제주", "4"): "1110",
    ("20261005", "제주", "5"): "1200", ("20261005", "제주", "6"): "1300", ("20261005", "제주", "7"): "1300"
}

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

# =========================================================================
# 🎯 [신규 기능] 삼복승 / 복연승 적중 유력 초엄격 판별 알고리즘
# =========================================================================
def evaluate_trio_confidence(race):
    """
    단거리(1200m 이하)에서 상위 3두의 능력치가 압도적이고,
    4위 이하와의 점수 차이가 확실하게 벌어진 경주만 선별 (자주 나오지 않음)
    """
    horses = race.get("horses", [])
    if len(horses) < 6:
        return False, ""

    try:
        dist = int(race.get("distance", "1200"))
    except:
        dist = 1200

    # 1. 거리 조건: 단거리(1200m 이하) 한정
    if dist > 1200:
        return False, ""

    h1, h2, h3 = horses[0], horses[1], horses[2]
    h4 = horses[3]

    s1, s2, s3, s4 = h1.get("ai_score", 0), h2.get("ai_score", 0), h3.get("ai_score", 0), h4.get("ai_score", 0)

    # 2. 점수 기준치 (능력치 상위 집중)
    cond_scores = (s1 >= 68.0 and s2 >= 62.0 and s3 >= 58.5)
    
    # 3. 3위와 4위의 격차(능력 분리형 경주)
    gap_3_4 = s3 - s4
    cond_gap = (gap_3_4 >= 3.2)

    # 4. 상위 3두 중 특급/상위 기수 및 스피드 지수 집중도
    top3_tags = (h1.get("ai_tags", []) + h2.get("ai_tags", []) + h3.get("ai_tags", []))
    jockey_power_cnt = sum(1 for t in top3_tags if "특급 기수" in t or "상위 기수" in t)
    speed_power_cnt = sum(1 for t in top3_tags if "스피드" in t or "황금게이트" in t)

    if cond_scores and cond_gap and (jockey_power_cnt >= 2) and (speed_power_cnt >= 2):
        return True, f"TOP 3 능력 분리 완성 (3-4위 격차 +{round(gap_3_4, 1)}점) • 스피드/기수 우위 완벽 집중"

    return False, ""

def fetch_meet_data(meet_code, meet_name, date_str):
    params = {
        "serviceKey": API_KEY,
        "pageNo": "1",
        "numOfRows": "150",
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
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()

        root = ET.fromstring(xml_data)
        items = root.findall(".//item")
        if not items:
            return []

        print(f"[{meet_name}] 마사회 데이터 수신: {len(items)}개 출전마")

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
            name = gv(["hrName", "hr_name"]) or "경주마"
            jockey = gv(["jkName", "jk_name"]) or "기수"
            trainer = gv(["trName", "tr_name"]) or "조교사"
            weight = gv(["wgBudam", "wg_budam"]) or "55.0"
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

            # 착순 정확 추출
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
                    "distance": "1200",
                    "track": track,
                    "version": VERSION,
                    "horses": []
                }

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
                "actual_ord": ord_no
            })

        for r in races.values():
            meet = r["meet_name"]
            r_no = str(int(r["race_no"])) if str(r["race_no"]).isdigit() else str(r["race_no"])

            dist_key = (date_str, meet, r_no)
            if dist_key in EXACT_RACE_DISTANCES:
                actual_dist = EXACT_RACE_DISTANCES[dist_key]
            else:
                fastest_sec = 999.0
                for h in r["horses"]:
                    s = parse_time_seconds(h["rc_time"])
                    if s and s > 20.0 and s < fastest_sec:
                        fastest_sec = s
                
                if fastest_sec < 900.0:
                    if meet == "제주":
                        actual_dist = "900" if fastest_sec < 64.0 else ("1000" if fastest_sec < 77.0 else "1110")
                    else:
                        actual_dist = "1000" if fastest_sec < 67.0 else ("1200" if fastest_sec < 78.5 else ("1400" if fastest_sec < 94.0 else "1800"))
                else:
                    actual_dist = "1200"

            r["distance"] = actual_dist
            dist = int(actual_dist)

            # 최고 부담중량
            all_weights = []
            for h in r["horses"]:
                try:
                    all_weights.append(float(re.sub(r'[^0-9.]', '', str(h["weight"]))))
                except:
                    all_weights.append(55.0)
            max_race_weight = max(all_weights) if all_weights else 55.0

            # 사전 순발력 파워 계산
            for h in r["horses"]:
                jk_r = JOCKEY_RATES.get(h["jockey"], 12.0)
                tr_r = TRAINER_RATES.get(h["trainer"], 14.0)
                g_val = int(h["gate"]) if str(h["gate"]).isdigit() else 5
                try:
                    w_val = float(re.sub(r'[^0-9.]', '', str(h["weight"])))
                except:
                    w_val = 55.0
                
                gate_power = 6.0 if g_val <= 3 else (4.0 if g_val <= 7 else 0.0)
                weight_power = (55.0 - w_val) * 1.5
                front_power = 10.0 if h["is_front"] else 0.0
                h["speed_power"] = jk_r * 0.8 + tr_r * 0.4 + gate_power + weight_power + front_power

            sorted_by_speed = sorted(r["horses"], key=lambda x: x["speed_power"], reverse=True)
            top_speed_gate = str(sorted_by_speed[0]["gate"]).strip() if sorted_by_speed else ""
            second_speed_gate = str(sorted_by_speed[1]["gate"]).strip() if len(sorted_by_speed) > 1 else ""

            # 사전 예상 점수 영구 고정 채점
            for h in r["horses"]:
                h["distance"] = str(dist)
                score = 30.0
                tags = []
                g = int(h["gate"]) if str(h["gate"]).isdigit() else 5
                this_gate = str(h["gate"]).strip()

                try:
                    clean_w = float(re.sub(r'[^0-9.]', '', str(h["weight"])))
                except:
                    clean_w = 55.0

                tot_rc = int(re.sub(r'[^0-9]', '', str(h.get("rc_cnt", "0"))) or 0)
                ord1_cnt = int(re.sub(r'[^0-9]', '', str(h.get("ord1_cnt", "0"))) or 0)
                ord2_cnt = int(re.sub(r'[^0-9]', '', str(h.get("ord2_cnt", "0"))) or 0)
                quinella_rate = round(((ord1_cnt + ord2_cnt) / tot_rc) * 100, 1) if tot_rc >= 3 else 20.0

                # 1. 기수 & 조교사 (거품 필터링)
                jk_rate = JOCKEY_RATES.get(h["jockey"], 12.0)
                if tot_rc >= 3 and quinella_rate < 15.0:
                    score += (jk_rate * 0.45)
                    tags.append("말 검증필요 ⚠️")
                else:
                    score += (jk_rate * 0.75)
                    if jk_rate >= 24.0:
                        tags.append("특급 기수 🏇")
                    elif jk_rate >= 19.0:
                        tags.append("상위 기수")

                tr_rate = TRAINER_RATES.get(h["trainer"], 14.0)
                score += (tr_rate * 0.5)
                if tr_rate >= 20.0:
                    tags.append("우수 마방 🏆")

                # 2. 거리별 게이트 가중치
                if dist <= 1300:
                    score += 6.0 if g <= 3 else (4.0 if g <= 7 else 0.0)
                    if g <= 3:
                        tags.append("단거리 황금게이트 ⚡")
                elif dist >= 1700:
                    score += 5.0 if g <= 4 else (3.0 if g <= 8 else 0.0)
                else:
                    score += 5.0 if g <= 4 else (3.0 if g <= 8 else 0.0)

                # 3. 게이트 적성
                if h["is_front"] and g <= 3:
                    score += 4.0
                    tags.append("인코스 찰떡궁합 🎯")
                elif (not h["is_front"]) and g >= 8:
                    score += 3.0
                    tags.append("외곽 모래회피 복병 🚀")

                # 4. 외곽 다크호스 레이더
                if g >= 8 and tr_rate >= 18.0 and 53.5 <= clean_w <= 56.5:
                    score += 6.0
                    tags.append("숨은 다크호스 💥")

                # 5. 부담중량 역학 (체급 최강자 탑웨이트 보정)
                if dist >= 1700 and clean_w <= 52.5:
                    score += 2.0
                    tags.append(f"경량 부중({clean_w}kg) ⚡")
                elif dist < 1700 and clean_w <= 52.5:
                    score += (55.0 - clean_w) * 1.8
                    tags.append(f"경량 부중({clean_w}kg) ⚡")
                elif clean_w >= 57.5 and clean_w == max_race_weight:
                    score += 5.0
                    tags.append("체급 최강자(탑웨이트) 🏋️")
                else:
                    score -= max(0.0, (clean_w - 55.0) * 0.7)

                # 6. 사전 스피드 뱃지 (영구 고정!)
                past_sec = parse_time_seconds(h.get("past_time", ""))
                if past_sec:
                    score += 8.0
                    tags.append(f"과거 스피드 최상({round(past_sec,1)}초) 🏎️")
                elif this_gate == top_speed_gate:
                    score += 8.0
                    tags.append("과거 스피드 최상 🏎️")
                elif this_gate == second_speed_gate:
                    score += 4.0
                    tags.append("스피드 우수 🏎️")

                # 7. 전적 복승률
                if tot_rc >= 3:
                    if quinella_rate >= 40.0:
                        score += 8.0
                        tags.append(f"통산 복승률 최상({quinella_rate}%) 🏎️")
                    elif quinella_rate >= 25.0:
                        score += 4.0
                        tags.append(f"검증된 입상마({quinella_rate}%)")

                # 8. 선행력
                if h["is_front"]:
                    score += 5.0
                    tags.append("선행 강세 🚀")

                # 9. 승급전
                if str(h.get("pre_ord", "")).strip() in ["1", "01"]:
                    score -= 5.0
                    tags.append("승급 첫 도전(검증 필요) 🧱")

                # 🏁 경기 후 실제 완주 기록 뱃지
                sec = parse_time_seconds(h.get("rc_time", ""))
                if sec:
                    base_time = {
                        800: 52.0, 900: 59.0, 1000: 65.5, 1110: 73.0, 1200: 74.8, 1300: 82.0, 1400: 88.5, 1600: 102.5, 1700: 111.5, 1800: 117.5, 2000: 133.0
                    }.get(dist, dist * 0.063 + 0.5)
                    diff = base_time - sec
                    if diff >= 1.0:
                        tags.append(f"스피드 지수 최상({round(sec,1)}초) 🏎️")
                    elif diff >= 0.0:
                        tags.append("기록 우수")

                # 🏁 경기 후 G1F 스퍼트 뱃지
                try:
                    m_g1f = re.search(r'(\d+\.?\d*)', str(h.get("g1f_time", "")))
                    if m_g1f:
                        g1f_val = float(m_g1f.group(1))
                        if 11.0 <= g1f_val <= 12.8:
                            tags.append(f"직선주로 스퍼트 최강({g1f_val}초) 🚀")
                except:
                    pass

                h["ai_score"] = round(score, 1)
                h["ai_tags"] = tags
                h["odds_display"] = "-"

            r["horses"].sort(key=lambda x: x["ai_score"], reverse=True)

            # 🎯 [신규] 삼복승/복연승 유력 경주 판정 플래그 부여
            is_target, reason = evaluate_trio_confidence(r)
            r["is_trio_target"] = is_target
            r["trio_reason"] = reason

        return list(races.values())

    except Exception as e:
        print(f"[{meet_name}] 통신 에러: {e}")
        return []

# =========================================================================
# 🎯 [V8.8 핵심] 5주치 누적 병합(Merge) 아카이브 수집기
# =========================================================================
def sync_5weeks_archive():
    now = datetime.now(KST)
    
    # 1. 기존 race_data.json 파일이 있으면 먼저 불러와서 보존!
    existing_races = {}
    if os.path.exists("race_data.json"):
        try:
            with open("race_data.json", "r", encoding="utf-8") as f:
                old_list = json.load(f)
                for r in old_list:
                    k = f"{r.get('race_date')}_{r.get('meet_name')}_{r.get('race_no')}"
                    existing_races[k] = r
            print(f"📦 기존 저장소에서 {len(existing_races)}개 과거 경주 로드 완료")
        except Exception:
            existing_races = {}

    # 2. 수집 대상 날짜: 어제, 오늘, 내일 (실시간 최신 반영)
    dates_to_fetch = [
        (now - timedelta(days=1)).strftime("%Y%m%d"), # 어제 (10/3 토 복기 확실 보존!)
        now.strftime("%Y%m%d"),                        # 오늘 (10/4 일 실시간)
        (now + timedelta(days=1)).strftime("%Y%m%d")  # 내일 (10/5 월 대체공휴일 사전예상)
    ]

    print(f"🔄 최신 데이터 수집 대상 날짜: {dates_to_fetch}")
    for dt in dates_to_fetch:
        for m_code, m_name in MEET_CONFIG:
            res = fetch_meet_data(m_code, m_name, dt)
            for r in res:
                k = f"{r.get('race_date')}_{r.get('meet_name')}_{r.get('race_no')}"
                existing_races[k] = r  # 덮어쓰거나 새로 추가 (누적 병합!)

    # 3. 5주(35일) 필터링: 35일이 지난 너무 오래된 데이터만 자동 정리!
    cutoff_date = (now - timedelta(days=35)).strftime("%Y%m%d")
    final_list = []
    for k, r in existing_races.items():
        r_date = str(r.get("race_date", ""))
        if r_date >= cutoff_date:
            # 기존 과거 데이터 중 is_trio_target이 누락된 항목도 재검사하여 보정
            if "is_trio_target" not in r:
                is_target, reason = evaluate_trio_confidence(r)
                r["is_trio_target"] = is_target
                r["trio_reason"] = reason
            final_list.append(r)

    return final_list

def main():
    if not API_KEY:
        print("❌ KRA_API_KEY 미설정")
        return

    all_races = sync_5weeks_archive()

    if all_races:
        meet_order = {"서울": 1, "부산경남": 2, "영천": 3, "제주": 4}
        # 날짜 오름차순(과거 ➔ 최신), 경마장 순, 경주번호 순 정렬
        all_races.sort(key=lambda x: (
            x["race_date"],
            meet_order.get(x["meet_name"], 9),
            int(x["race_no"]) if str(x["race_no"]).isdigit() else 99
        ))
        with open("race_data.json", "w", encoding="utf-8") as f:
            json.dump(all_races, f, ensure_ascii=False, indent=2)
        print(f"🎉 성공: [{VERSION}] 5주 누적 아카이브 갱신 완료! (총 {len(all_races)}개 경주 영구 보존)")
    else:
        print("❌ 데이터를 가져오지 못했습니다.")

if __name__ == "__main__":
    main()
