"""한국모태펀드 자조합 현황(2025-12-31)으로 운용사별 조합 수 분포를 집계한다.

입력: data/kvic_subfunds_20251231.csv (연번, 조합명, 대표GP, 조합결성일, 결성총액(백만원))
출력: docs/07-gp-distribution.md

주의: 이 파일은 모태펀드가 출자한 자조합만 담는다. 모태 출자 없는 조합(민간 단독, 신기술조합 다수)은 빠져 있어
운용사별 조합 수는 하한(undercount)이고, 모태 출자 이력이 없는 운용사는 아예 나타나지 않는다.
"""

import collections
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "kvic_subfunds_20251231.csv"
OUT = ROOT / "docs" / "07-gp-distribution.md"

ACTIVE_FROM = 2018   # 존속기간 8년 가정 → 2018년 이후 결성분을 '운용 중'으로 본다
BUCKETS = [(1, 2, "1~2"), (3, 5, "3~5"), (6, 10, "6~10"), (11, 20, "11~20"), (21, 999, "21+")]

# 대표GP 이름으로 회사 유형을 거칠게 분류한다. 정확한 등록 구분은 금감원·중기부 명부로 대체해야 한다.
TYPE_RULES = [
    ("증권·금투 겸영", re.compile(r"증권|금융투자|투자증권|자산운용")),
    ("캐피탈·카드·은행 겸업", re.compile(r"(?<!벤처)캐피탈|카드|은행|파이낸셜|저축")),
    ("기술투자(신기사형)", re.compile(r"기술투자|신기술|테크놀로지인베스트|기술금융")),
    ("공공·정책", re.compile(r"한국벤처투자|산업은행|중소기업은행|기업은행|성장금융|한국성장")),
    ("LLC·파트너스형", re.compile(r"파트너스$|파트너스\(|LLC|엘엘씨")),
]


def classify(name):
    for label, rx in TYPE_RULES:
        if rx.search(name):
            return label
    return "일반 벤처투자회사(추정)"


def bucket(n):
    for lo, hi, label in BUCKETS:
        if lo <= n <= hi:
            return label
    return "0"


def main():
    rows = []
    with open(SRC, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r = {k.strip(): v.strip() for k, v in r.items()}
            rows.append(dict(gp=r["대표GP"], year=int(r["조합결성일"][:4]), amt=int(r["결성총액(백만원)"])))

    total = collections.Counter(r["gp"] for r in rows)
    active = collections.Counter(r["gp"] for r in rows if r["year"] >= ACTIVE_FROM)
    active_amt = collections.defaultdict(int)
    for r in rows:
        if r["year"] >= ACTIVE_FROM:
            active_amt[r["gp"]] += r["amt"]

    by_year = collections.Counter(r["year"] for r in rows)
    amt_by_year = collections.defaultdict(int)
    for r in rows:
        amt_by_year[r["year"]] += r["amt"]

    # 분포 (운용 중 기준)
    dist = collections.Counter(bucket(n) for n in active.values())
    dist_total = collections.Counter(bucket(n) for n in total.values())

    # 유형별
    type_of = {gp: classify(gp) for gp in total}
    type_cnt = collections.Counter(type_of[gp] for gp in active)
    type_funds = collections.Counter()
    type_dist = collections.defaultdict(collections.Counter)
    for gp, n in active.items():
        type_funds[type_of[gp]] += n
        type_dist[type_of[gp]][bucket(n)] += 1

    labels = [b[2] for b in BUCKETS]
    out = []
    out.append("# 운용사별 조합 수 분포 (영역 A 보강) — 모태펀드 자조합 현황 2025-12-31")
    out.append("")
    out.append("> 생성: `python model/gp_distribution.py` · 원본: `data/kvic_subfunds_20251231.csv` (data.go.kr 한국모태펀드 자조합 현황)")
    out.append(f"> 운용 중 = 결성일 {ACTIVE_FROM}년 이후(존속 8년 가정). 유형은 GP 이름 패턴으로 추정한 것이며 등록 구분이 아니다.")
    out.append("")
    out.append("## 0. 이 데이터의 한계 (먼저 읽을 것)")
    out.append("")
    out.append("- **모태펀드가 출자한 자조합만** 들어 있다. 민간 LP만으로 결성된 조합과 신기술사업투자조합 대다수는 빠져 있다.")
    out.append("- 따라서 운용사별 조합 수는 **하한**이고, 모태 출자 이력이 없는 운용사(전업 신기사 상당수)는 **아예 나타나지 않는다**.")
    out.append("- 쓸 수 있는 것: 분포의 **모양**(소수 대형사 + 다수 소형사), 벤처투자회사 세그먼트 크기의 하한, 결성 추이.")
    out.append("- 쓸 수 없는 것: 신기사 세그먼트 크기. 이건 여전히 금감원·여신협회 명부가 필요하다.")
    out.append("")
    out.append("## 1. 전체 규모")
    out.append("")
    out.append(f"- 자조합 총 {len(rows):,}개, 결성총액 {sum(r['amt'] for r in rows)/1e6:,.1f}조 원 (2004~2025 누적)")
    out.append(f"- 대표GP {len(total)}곳 (누적), 그중 {ACTIVE_FROM}년 이후 결성 조합을 가진 GP **{len(active)}곳**")
    out.append(f"- 운용 중(추정) 조합 {sum(active.values()):,}개, {sum(active_amt.values())/1e6:,.1f}조 원")
    out.append("")
    out.append("## 2. 연도별 결성 추이")
    out.append("")
    out.append("| 연도 | 결성 수 | 결성총액(억) |")
    out.append("|---|---|---|")
    for y in sorted(by_year):
        out.append(f"| {y} | {by_year[y]} | {amt_by_year[y]/100:,.0f} |")
    out.append("")
    out.append("## 3. 운용사별 운용 중 조합 수 분포")
    out.append("")
    out.append("| 조합 수 | GP 수 (운용 중 기준) | 비중 | GP 수 (누적 전체 기준) |")
    out.append("|---|---|---|---|")
    n_active = len(active)
    for lb in labels:
        out.append(f"| {lb} | {dist[lb]} | {dist[lb]/n_active:.0%} | {dist_total[lb]} |")
    out.append(f"| **합계** | **{n_active}** | | **{len(total)}** |")
    out.append("")
    s1 = dist["1~2"] + dist["3~5"]
    s2 = dist["6~10"] + dist["11~20"]
    s3 = dist["21+"]
    out.append(f"계획서 세그먼트로 환산(모태 출자 GP 한정): **S1(1~5) {s1}곳 · S2(6~20) {s2}곳 · S3(21+) {s3}곳**")
    out.append("")
    out.append("## 4. GP 유형(이름 패턴 추정)별")
    out.append("")
    out.append("| 유형 | GP 수 | 운용 중 조합 | GP당 평균 | " + " | ".join(labels) + " |")
    out.append("|---|---|---|---|" + "---|" * len(labels))
    for t, c in sorted(type_cnt.items(), key=lambda x: -x[1]):
        row = f"| {t} | {c} | {type_funds[t]} | {type_funds[t]/c:.1f} | "
        row += " | ".join(str(type_dist[t][lb]) for lb in labels) + " |"
        out.append(row)
    out.append("")
    out.append("## 5. 운용 중 조합 수 상위 30 GP")
    out.append("")
    out.append("| 순위 | 대표GP | 유형(추정) | 운용 중 조합 | 누적 조합 | 운용 중 결성총액(억) |")
    out.append("|---|---|---|---|---|---|")
    for i, (gp, n) in enumerate(active.most_common(30), 1):
        out.append(f"| {i} | {gp} | {type_of[gp]} | {n} | {total[gp]} | {active_amt[gp]/100:,.0f} |")
    out.append("")
    out.append("## 6. 시장 규모·모델에 반영할 것")
    out.append("")
    med = sorted(active.values())[len(active) // 2]
    out.append(f"- 운용 중 조합 수 중앙값 **{med}개**, 평균 {sum(active.values())/n_active:.1f}개. 롱테일이다: "
               f"GP의 {s1/n_active:.0%}가 조합 5개 이하(모태 출자분만 세어도).")
    out.append(f"- 모태 출자 GP만으로도 S2가 {s2}곳, S3가 {s3}곳 → `01-market-size.md`의 S2 150·S3 100 가정은 VC 세그먼트에서 "
               f"**과대**였다. 모태 미출자 조합을 더해도 S3는 50곳 안팎이 상한일 가능성이 높다.")
    out.append("- 캐피탈·증권 겸영 GP가 모태 자조합에도 다수 등장한다 → 이들은 벤처투자조합과 신기술조합을 함께 운용하는 S4 혼합형이며, "
               "로고스 등 VC ERP 도입 가능성이 높은 집단이다.")
    out.append("- 신기사 전업(전업 신기술금융사)은 이 파일에 거의 없다 → 신기사 세그먼트 크기는 여전히 미실측. 금감원 등록 명부가 필요하다.")
    OUT.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"GPs active={n_active} dist={dict(dist)} types={dict(type_cnt)}")


if __name__ == "__main__":
    main()
