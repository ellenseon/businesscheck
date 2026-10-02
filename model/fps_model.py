"""FPS 3개년 재무 시나리오 모델.

모든 금액 단위: 만원. 가정은 docs/01-market-size.md, docs/05-pricing-and-cost.md 참조.
실행: python model/fps_model.py  → docs/06-financial-model.md 를 다시 생성한다.
"""

from dataclasses import dataclass, field


@dataclass
class Segment:
    name: str
    sam: int                 # 영업 가능 회사 수
    price: int               # 연 구독료
    onboarding_fee: int      # 초기 도입비(1회)
    support_cost: int        # 고객당 연간 지원 원가
    conv: tuple              # 연도별 누적 전환율 (y1, y2, y3)


@dataclass
class Scenario:
    name: str
    segments: list
    dev_cost: int            # 연간 고정 개발·개정 대응 원가 (인건비)
    sales_cost: int          # 연간 고정 영업·마케팅 원가
    note: str = ""
    rows: list = field(default_factory=list)

    def run(self):
        self.rows = []
        prev = {s.name: 0 for s in self.segments}
        for y in range(3):
            cust = {s.name: round(s.sam * s.conv[y]) for s in self.segments}
            new = {k: cust[k] - prev[k] for k in cust}
            sub = sum(cust[s.name] * s.price for s in self.segments)
            onb = sum(new[s.name] * s.onboarding_fee for s in self.segments)
            var = sum(cust[s.name] * s.support_cost for s in self.segments)
            # 신규 고객 이관 공수: 도입비로 회수한다고 가정하되 50%는 원가로 본다
            onb_cost = onb * 0.5
            fixed = self.dev_cost + self.sales_cost
            rev = sub + onb
            cost = var + onb_cost + fixed
            self.rows.append(dict(year=y + 1, cust=sum(cust.values()), cust_by=cust,
                                  sub=sub, onb=onb, rev=rev, var=var + onb_cost,
                                  fixed=fixed, profit=rev - cost))
            prev = cust
        return self

    def breakeven_customers(self):
        # 가중평균 공헌이익(구독료 - 지원원가)으로 손익분기 고객 수
        w = sum(s.sam for s in self.segments)
        contrib = sum((s.price - s.support_cost) * s.sam for s in self.segments) / w
        return round((self.dev_cost + self.sales_cost) / contrib)


def seg(sam, price, onb, cost, conv):
    return sam, price, onb, cost, conv


SCENARIOS = [
    Scenario("보수", [
        Segment("S1 소형", 100, 360, 300, 450, (0.02, 0.04, 0.06)),
        Segment("S2 중형", 100, 900, 800, 500, (0.03, 0.06, 0.10)),
        Segment("S3 대형", 40, 2400, 1500, 650, (0.025, 0.05, 0.075)),
    ], dev_cost=12000, sales_cost=6000,
        note="신기사 전문으로 축소. 로고스·똑똑이 신기사 보고서를 일부 지원해 공백이 작은 경우"),
    Scenario("기준", [
        Segment("S1 소형", 130, 360, 300, 450, (0.03, 0.08, 0.12)),
        Segment("S2 중형", 150, 900, 800, 500, (0.04, 0.10, 0.16)),
        Segment("S3 대형", 50, 2400, 1500, 650, (0.04, 0.10, 0.16)),
    ], dev_cost=12000, sales_cost=6000,
        note="신기사 업무보고서 자동화가 실제 공백이고, 디자인 파트너 3곳으로 출발"),
    Scenario("낙관", [
        Segment("S1 소형", 130, 420, 300, 400, (0.05, 0.12, 0.20)),
        Segment("S2 중형", 150, 1000, 800, 450, (0.06, 0.15, 0.25)),
        Segment("S3 대형", 50, 3000, 2000, 600, (0.06, 0.14, 0.24)),
    ], dev_cost=14000, sales_cost=8000,
        note="공백 확인 + 금감원 원천데이터 전환이 원장 수요를 키우는 경우. 영업 투자 확대"),
]


def fmt(n):
    return f"{n:,.0f}"


def render(scenarios):
    out = ["# 재무 모델 (영역 H) — 3개년 시나리오",
           "",
           "> 생성: `python model/fps_model.py`. 단위: 만원. 가정은 `01-market-size.md`, `05-pricing-and-cost.md`.",
           "> 고정비: 개발 2명(개정 대응 포함) + 영업 1명 수준. 인터뷰 후 전환율·가격을 교체해 재실행한다.",
           ""]
    out += ["## 1. 시나리오 가정", "",
            "| 시나리오 | 세그먼트 | SAM | 연 구독료 | 도입비 | 지원원가 | 누적 전환율 Y1/Y2/Y3 |",
            "|---|---|---|---|---|---|---|"]
    for sc in scenarios:
        for s in sc.segments:
            out.append(f"| {sc.name} | {s.name} | {s.sam} | {fmt(s.price)} | {fmt(s.onboarding_fee)} | "
                       f"{fmt(s.support_cost)} | {s.conv[0]:.0%}/{s.conv[1]:.0%}/{s.conv[2]:.0%} |")
    out += ["", "| 시나리오 | 고정비(개발+영업)/년 | 전제 |", "|---|---|---|"]
    for sc in scenarios:
        out.append(f"| {sc.name} | {fmt(sc.dev_cost + sc.sales_cost)} | {sc.note} |")
    out += ["", "## 2. 결과", ""]
    for sc in scenarios:
        out += [f"### {sc.name}", "",
                "| 연도 | 고객 수 (S1/S2/S3) | 구독 매출 | 도입비 매출 | 총매출 | 변동원가 | 고정비 | 영업이익 |",
                "|---|---|---|---|---|---|---|---|"]
        for r in sc.rows:
            by = "/".join(str(v) for v in r["cust_by"].values())
            out.append(f"| Y{r['year']} | {r['cust']} ({by}) | {fmt(r['sub'])} | {fmt(r['onb'])} | "
                       f"**{fmt(r['rev'])}** | {fmt(r['var'])} | {fmt(r['fixed'])} | **{fmt(r['profit'])}** |")
        out.append(f"\n손익분기 고객 수(고정비 기준, 가중평균 공헌이익): **약 {sc.breakeven_customers()}사**\n")
    out += ["## 3. 읽는 법", "",
            "- **보수 시나리오는 3년 내 손익분기에 못 미친다**(Y3 영업이익 −0.66억). 기준 시나리오는 Y2에 간신히 흑자(+0.26억), "
            "Y3 매출 6억·이익 1.1억. 낙관은 Y3 매출 11억·이익 4.1억. 즉 성립 여부는 전적으로 '신기사 보고서 자동화가 실제 공백인가'(기준 vs 보수 분기점)에 달려 있다.",
            "- 손익분기 고객 수는 **35~44사**. 신기사 SAM(~280)의 **13~16%** 침투가 필요하다 — 고정비 3명 규모에서도 니치 치고 높은 침투율이며, "
            "그 사이 로고스·똑똑이 같은 기능을 추가하면 보수 시나리오로 떨어진다.",
            "- 매출 규모 자체가 작다: 낙관 Y3도 11억. 이 사업은 **단독 벤처가 아니라 소규모 전문 SW 회사 또는 기존 벤더의 모듈**로 적합한 크기다.",
            "- 수익은 S2·S3에서 나온다. S1(소형)은 지원 원가가 구독료를 잠식한다 → S1은 셀프 온보딩 SaaS가 아니면 받지 않는 것이 낫다.",
            "- 가장 민감한 변수는 (1) S2·S3 전환율 (2) S3 단가 (3) 설치형 지원 원가. 인터뷰 15건 중 S2·S3 응답으로 이 세 값을 먼저 교체할 것.",
            "- 긍정 시나리오가 성립하려면 **인접 매출(LP 보고서, 공정가치, 보수 계산, 원천데이터 제출)** 또는 **기존 벤더에 대한 모듈 공급/인수**가 "
            "로드맵에 있어야 한다. 모델에는 포함하지 않았다."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import pathlib
    for sc in SCENARIOS:
        sc.run()
    path = pathlib.Path(__file__).resolve().parent.parent / "docs" / "06-financial-model.md"
    path.write_text(render(SCENARIOS), encoding="utf-8")
    for sc in SCENARIOS:
        print(sc.name, [(r["year"], r["cust"], r["rev"], r["profit"]) for r in sc.rows], "BE:", sc.breakeven_customers())
