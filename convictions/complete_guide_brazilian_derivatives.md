# Complete Guide to Brazilian Derivatives Markets
## Decade Investment Research | Internal Conviction Document
### For Advisor and Institutional Client Use

---

> **Intended Audience**: Decade advisors and sophisticated clients seeking a practical and comprehensive understanding of Brazilian derivatives — from market structure and product mechanics through hedging strategies and regulatory compliance. This document assumes familiarity with basic financial concepts but does not assume prior derivatives experience specific to Brazil.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The B3 Derivatives Ecosystem](#b3-ecosystem)
3. [DI Futures: The Heartbeat of Brazilian Fixed Income](#di-futures)
4. [Dollar Futures and FX Derivatives](#dollar-futures)
5. [Ibovespa Futures](#ibovespa-futures)
6. [Commodity Futures on B3](#commodity-futures)
7. [Options Markets: Equity and Index Options](#options-markets)
8. [Swaps: CDI x IPCA, CDI x Fixed, Cross-Currency](#swaps)
9. [Forward Contracts (NDF and Termo)](#forward-contracts)
10. [B3 Clearing and Settlement Architecture](#b3-clearing)
11. [Margin Requirements and Risk Management](#margin-requirements)
12. [Hedging Strategies for Equity Portfolios](#equity-hedging)
13. [FX Hedging for Importers and Exporters](#fx-hedging)
14. [Using DI Futures to Manage Interest Rate Risk](#di-hedging)
15. [Basis Risk](#basis-risk)
16. [Roll Strategies](#roll-strategies)
17. [Contango vs. Backwardation in Brazilian Commodity Markets](#contango-backwardation)
18. [Regulatory Framework](#regulatory-framework)
19. [Taxation of Derivatives](#taxation)
20. [Institutional vs. Retail Use Cases](#institutional-vs-retail)
21. [Practical Reference Tables](#reference-tables)

---

## 1. Executive Summary {#executive-summary}

Brazil's derivatives market, operated through B3 (Brasil, Bolsa, Balcão — the unified exchange created by the 2008 merger of BM&F and Bovespa, which further merged with Cetip in 2017), is one of the largest and most sophisticated in the emerging world. By notional value outstanding, the Brazilian derivatives market ranks among the top ten globally, driven by the unique characteristics of Brazil's financial system: high and volatile interest rates, a commodity-heavy export profile, and a structurally active foreign exchange market.

The defining feature of Brazilian derivatives is the **DI futures contract** — a futures contract on the accumulated CDI rate over a defined period. The DI futures market is the primary instrument through which market participants price and hedge interest rate risk in Brazil. Its liquidity rivals or exceeds that of OTC interest rate derivatives in most emerging markets, and the DI curve is the reference yield curve for virtually all BRL fixed income pricing.

Key themes for advisors:

- **DI futures are indispensable for fixed income portfolio management.** Any manager with meaningful exposure to pre-fixed or IPCA-linked bonds needs to understand DI futures to manage duration and convexity.
- **Dollar futures (DOL and WDO) are the primary FX hedging instruments** for Brazilian corporates and funds. The "casado" (basis between onshore BRL/USD and the futures price) is a critical variable.
- **B3's integrated clearing model (CCP)** provides robust risk management but imposes margin calls that require liquidity management attention.
- **Options liquidity is concentrated in a small number of liquid underlyings** (Petrobras, Vale, Ibovespa index). For most equity positions, OTC options or synthetic positions using futures are more practical.
- **Taxation of derivatives is complex** and differs between domestic and foreign investors, between exchange-traded and OTC contracts, and between hedging and speculative positions.

---

## 2. The B3 Derivatives Ecosystem {#b3-ecosystem}

### B3: Structure and Market Segments

B3 S.A. — Brasil, Bolsa, Balcão is the sole organized securities and derivatives exchange in Brazil. It operates the following relevant segments:

**BM&FBovespa Segment (derivatives, fixed income, FX):**
- Futures contracts (DI, dollar, Ibovespa, commodity)
- Options on futures
- Swaps registered and guaranteed by B3 (via clearing)
- FX spot auctions (secondary market)

**Bovespa Segment (equities):**
- Equity spot market
- Equity options (calls and puts on individual stocks)
- Equity forward contracts (termo)

**Cetip Segment (OTC registration and clearing):**
- OTC swaps registration and settlement
- Debenture registration
- CDB and LCA/LCI registration

### Market Hours

| Session | Time (Brasília) | Products |
|---|---|---|
| Pre-market | 09:00 | Some equity derivatives |
| Regular trading | 09:00 – 18:00 | All exchange products |
| After-market equity | 18:00 – 18:25 | Equity spot only |
| Extended futures | 09:00 – 18:15 | DI, dollar, Ibovespa futures |
| Electronic after-hours | 17:00 – 20:00 (US time) | Dollar futures (aligned with US close) |

Dollar futures and DI futures have extended hours due to the interaction with US and global markets.

### Participants

The Brazilian derivatives market serves several categories of participants:

| Participant Type | Primary Role | Key Instruments |
|---|---|---|
| Commercial banks | Hedging and market-making | DI futures, dollar futures, swaps |
| Investment funds | Hedging, speculation, yield enhancement | All instruments |
| Non-financial corporates | FX and interest rate hedging | Dollar futures, swaps, NDF |
| Pension funds (EFPC) | ALM hedging, yield overlay | NTN-B-linked swaps, DI futures |
| Foreign investors | Macro trading, EM exposure | Dollar futures, DI futures, swaps |
| Retail investors | Speculation, income strategies | Mini contracts (WDO, WIN), equity options |
| Broker-dealers | Market-making, structured products | All instruments |

---

## 3. DI Futures: The Heartbeat of Brazilian Fixed Income {#di-futures}

### Contract Specifications

The **Contrato Futuro de Taxa Média de Depósitos Interfinanceiros de Um Dia (DI1)** is the most liquid financial futures contract in Latin America and among the most traded interest rate futures globally by daily turnover.

| Feature | Specification |
|---|---|
| Underlying | Accumulated CDI rate from trade date to expiry date |
| Contract size | BRL 100,000 (notional face value at maturity) |
| Quotation | Annual interest rate (252 business day basis), e.g., 11.50% |
| PU (unit price) | PU = 100,000 / (1 + rate)^(n/252), where n = business days to expiry |
| Expiry dates | First business day of each month |
| Last trading day | Last business day of the month preceding expiry |
| Settlement | Financial, daily MTM + final settlement in BRL |
| Minimum tick | 0.001 percentage point (0.1 bp) |
| Clearing | B3 (central counterparty) |
| Margin | Initial margin required (varies by tenor and volatility) |

**Important conventions**: DI futures trade in rate terms, but gains/losses are calculated on the PU (unit price). This creates convexity — a non-linear relationship between rate movements and P&L.

### How DI Futures Work: A Practical Example

Suppose the DI Jan27 contract trades at a rate of 12.00% per year (252-day basis). The trade date has 500 business days to the January 2027 expiry.

- **PU at trade**: 100,000 / (1.12)^(500/252) = approximately 79,590
- If the DI rate rises to 12.50%, the new PU = 100,000 / (1.125)^(500/252) ≈ 78,960
- **P&L per contract**: 78,960 – 79,590 = –630 PU points per contract = –BRL 630 per contract

This illustrates that **rising DI rates generate losses for DI future buyers (long position in PU terms)** and gains for sellers (short position in PU terms). Since DI futures are typically quoted in rate terms, traders who think rates will rise "sell" DI futures (i.e., they buy the right to receive the fixed rate and pay the floating CDI — equivalent to receiving fixed in an IRS).

### DI Futures Curve Construction

The DI curve is quoted as a series of rates for monthly expiry dates extending up to 5–7 years. The curve has several regions:

- **Short end (0–1 year)**: Reflects current Selic target and near-term Copom meeting expectations. Very liquid, tight bid-ask.
- **Medium term (1–3 years)**: Incorporates inflation expectations, fiscal risk premium, and expected rate normalization path.
- **Long end (3–7+ years)**: Reflects structural risk premium, fiscal sustainability concerns, and term premium. Less liquid; bid-ask spreads wider.

**The DI curve is the primary tool for extracting market-implied Copom decisions.** By comparing consecutive monthly DI futures, traders can derive the expected rate change at each Copom meeting and the probability of 25 vs. 50 bp moves.

### DI Futures vs. NTN-B and NTN-F Pricing

- **NTN-F (pre-fixed government bonds)**: Priced as present value of fixed coupons and face value, discounted at the DI curve (adjusted for the pre-fixed spread). The DI curve is the primary input.
- **NTN-B (IPCA + real rate)**: Priced using a real interest rate curve. The relationship to DI futures is indirect but important — changes in the DI curve affect the implied breakeven inflation (IPCA implied by NTN-B real yield vs. NTN-F nominal yield).
- **DAP futures (IPCA futures)**: B3 lists DAP (Diferencial de Acumulação de IPCA) futures, which allow trading of accumulated IPCA over a period. These are less liquid than DI futures but useful for expressing inflation views.

---

## 4. Dollar Futures and FX Derivatives {#dollar-futures}

### The Two Dollar Futures Contracts

B3 lists two USD/BRL futures contracts:

**DOL (Full Dollar Futures)**:
| Feature | Specification |
|---|---|
| Contract size | USD 50,000 |
| Quotation | BRL per USD 1,000 (e.g., 5.000 = BRL 5.00 per USD) |
| Expiry | First business day of each month |
| Settlement | Financial, in BRL at the PTAX rate (BCB official closing rate of the day prior to expiry) |
| Minimum tick | BRL 0.001 per USD 1,000 (= BRL 0.05 per contract) |
| Participants | Primarily institutions and corporates |

**WDO (Mini Dollar Futures)**:
| Feature | Specification |
|---|---|
| Contract size | USD 10,000 |
| Quotation | Same as DOL |
| Expiry | Same as DOL |
| Settlement | Financial, PTAX |
| Participants | Retail investors, smaller funds |

### PTAX: The Reference Rate

Settlement of all FX derivatives in Brazil references the **PTAX rate** published by the BCB. The PTAX is the average of four BCB FX survey rounds (at approximately 10:00, 11:00, 12:00 and 13:00 Brasília time), capturing the BRL/USD spot market. The final PTAX of each day is published at approximately 13:20–13:30.

**PTAX fixing risk**: Because PTAX is not the closing rate but an average of morning surveys, there is a structural mismatch between what participants observe during the trading day and the settlement price. Large option positions with strike near the spot rate can create fixing dynamics around PTAX calculation windows.

### The "Casado" (Cupom Cambial)

The "casado" is a uniquely Brazilian concept. Because the Brazilian FX market is primarily onshore (capital controls prevent true offshore arbitrage for some participants), the dollar futures market incorporates a **cupom cambial** — the implied USD yield embedded in the relationship between the futures price and the spot BRL/USD rate.

**Cupom cambial formula:**

Cupom = [(Futures Price / Spot Rate) - 1] × (252 / n) × 100

Where n = business days to expiry.

The cupom cambial represents the implied USD interest rate that Brazilian onshore participants can earn by investing in BRL (receiving CDI) and hedging the FX risk. It is broadly equivalent to offshore USD rates (SOFR/LIBOR) plus/minus a basis driven by:

- BCB FX swap auctions (major influence on the short end)
- Demand for FX hedge by Brazilian importers and foreign investors
- Dollar funding cost for domestic banks

When the cupom cambial is below SOFR + spread (i.e., BRL is "cheap" to hedge), this signals strong domestic demand for FX hedging (importers, foreign investors buying BRL bonds wanting to hedge FX exposure).

---

## 5. Ibovespa Futures {#ibovespa-futures}

### Contract Specifications

**IND (Full Ibovespa Futures)**:
| Feature | Specification |
|---|---|
| Underlying | Ibovespa Index |
| Contract size | BRL 1 per index point (BRL ≈ 125,000–150,000 per contract at index ~125,000–150,000 pts) |
| Expiry | Wednesday nearest to the 15th of February, April, June, August, October, December |
| Settlement | Financial, based on Ibovespa closing value on expiry Wednesday |
| Minimum tick | 5 index points |
| Participants | Institutions primarily |

**WIN (Mini Ibovespa Futures)**:
| Feature | Specification |
|---|---|
| Contract size | BRL 0.20 per index point |
| Expiry | Same as IND |
| Participants | Retail and smaller funds |

### Basis and Fair Value

The theoretical fair value of Ibovespa futures incorporates:

**Fair Value = Spot × (1 + CDI)^(n/252) – PV(Dividends)**

Where:
- CDI = prevailing interest rate over the futures period
- n = business days to expiry
- PV(Dividends) = present value of expected dividends to be paid before expiry

The futures typically trade at a discount to spot (reflecting the dividend yield) or at a premium (if the CDI rate exceeds the dividend yield). In Brazil's high-interest-rate environment, the futures have historically traded at a significant discount to spot because the CDI rate is usually well above the Ibovespa's dividend yield (which averages 3–5% annually).

**Key implication for equity managers**: Using Ibovespa futures to replicate equity exposure carries a carry cost equal to CDI minus dividend yield. When CDI is high (e.g., 12–14%), the cost of equity futures replication is substantial, making long futures strategies less attractive than direct stock ownership for long-term holders.

### Using Ibovespa Futures for Portfolio Management

- **Beta hedging**: Selling IND or WIN futures reduces the market beta of a portfolio without selling individual stocks (avoiding transaction costs and market impact).
- **Cash equitization**: Funds receiving large inflows can "equitize" cash by buying WIN/IND futures immediately, then gradually building the physical equity portfolio.
- **Tactical sector-neutral views**: A manager with a positive view on a specific sector but negative view on the overall market can be long sector stocks + short IND futures.

---

## 6. Commodity Futures on B3 {#commodity-futures}

### Key Commodity Contracts

B3 lists several commodity futures, though liquidity varies considerably:

| Contract | Underlying | Contract Size | Most Liquid Expiries |
|---|---|---|---|
| BGI | Live Cattle (boi gordo) | 330 arrobas (@ ~15 kg/arroba) | Monthly, near-term |
| ICF | Arabica Coffee | 100 bags (60 kg each) | March, May, July, Sep, Dec |
| ACF | Ethanol (anhydrous) | 30 cubic meters | Monthly |
| SFI | Soybeans | 27 metric tons | Mar, Apr, May, Jun, Jul, Aug, Sep |
| MIL | Corn | 27 metric tons | Less liquid |
| OZG | Gold | 250 grams | Active |

**Practical note**: B3 commodity futures for agricultural products (coffee, soybeans, corn) are less liquid than their CME counterparts. Brazilian traders frequently use Chicago CME contracts for price discovery and basis management, then use B3 contracts for physical delivery or domestic hedge documentation purposes.

### B3 vs. CME for Brazilian Commodity Hedgers

For a Brazilian soy farmer:
- **Price discovery**: CBOT (CME) soybeans (ZS) are the primary reference
- **Local basis**: B3 SFI contract incorporates Brazilian port basis (Paranaguá or Santos)
- **Currency component**: A farmer wanting to hedge soybean prices fully must hedge both the commodity price (CBOT) and the BRL/USD exchange rate (B3 DOL or WDO)

This creates a **natural two-leg hedge** for Brazilian agricultural exporters, which is discussed further in the FX hedging section.

---

## 7. Options Markets: Equity and Index Options {#options-markets}

### Equity Options on B3

B3 lists American-style call and put options on individual stocks. The most liquid underlyings are:

- **PETR4** (Petrobras PN): By far the most liquid individual equity options market in Brazil
- **VALE3** (Vale ON): Second most liquid
- **BBDC4** (Bradesco PN), **BBAS3** (Banco do Brasil), **ITUB4** (Itaú): Significant but less liquid
- **BOVA11** (Ibovespa ETF): Options on the ETF provide liquid index options exposure

**Key conventions for B3 equity options:**

- **American exercise** (can be exercised any time before expiry)
- **Expiry**: Third Monday of each month (equity stock options); first business day nearest the 15th for index options
- **Settlement**: Physical delivery (exercise results in actual stock delivery) for most equity options; cash settlement for index options
- **Quotation**: Premium in BRL per share

**Strike price structure**: Historically, Brazilian equity options used letter codes for strikes (A = January call, B = February call, etc.; M = January put, N = February put, etc.) with the strike embedded in the option code. B3 has been transitioning toward more standardized coding.

### Ibovespa Index Options

B3 lists options on the Ibovespa futures (OI) and on the Ibovespa ETF (BOVA11). These are typically European-style (exercise only at expiry) for index options on futures.

### Implied Volatility Surface

The implied volatility surface for Brazilian equity options has several noteworthy structural features:

1. **Skew**: Brazilian options markets exhibit significant negative skew (put options carry higher implied vol than calls at equidistant strikes), driven by tail risk from political events and fiscal crises.

2. **Term structure**: Short-dated options are more sensitive to event risk (e.g., Copom meetings, IPCA releases, election dates). Implied vol typically spikes around known event dates.

3. **Realized vs. implied gap**: Brazilian equities have historically realized lower volatility than implied, suggesting options sellers have been compensated for selling vol. However, this relationship breaks down during extreme events.

### Practical Options Strategies for Brazilian Portfolios

**Protective puts**: Long equity positions can be hedged with long puts on PETR4, VALE3, or BOVA11 (OTM puts on BOVA11 are the most efficient index-level hedge given lower transaction costs than buying multiple single-stock puts).

**Covered calls (lançamento coberto)**: Extremely popular among Brazilian retail and HNW investors. Selling covered calls against long equity positions generates premium income (equivalent to reducing the effective dividend yield shortfall relative to CDI). This is one of the most common structured strategies in the Brazilian wealth management market.

**Collars**: Combining long protective put + short covered call. Creates a band of protection at zero net premium cost (approximately). Used by founders and large shareholders to hedge concentrated equity positions.

**Cash-covered puts**: Selling put options with cash collateral. Popular alternative to buying stocks at a target price; the investor receives premium income while waiting for the stock to reach the desired entry price.

---

## 8. Swaps: CDI x IPCA, CDI x Fixed, Cross-Currency {#swaps}

### The Brazilian Swap Market Structure

Swaps in Brazil are primarily registered and settled through **B3's OTC derivatives module** (formerly Cetip). This provides:
- Central registration (mandatory for regulated entities)
- Guaranteed settlement (optional, but most institutional swaps carry B3 guarantee)
- Daily MTM and margin call requirements for guaranteed swaps

### CDI x Pre-Fixed Swaps (DI x Pré)

The most common swap type in Brazil:
- **Paying leg**: CDI + spread (floating, reset daily)
- **Receiving leg**: Fixed rate (pre-fixed, paid at maturity or with periodic coupons)

**Economic equivalent**: Identical to a DI futures position (though swaps can be customized for any notional, maturity, and cash flow schedule, making them more flexible than standardized futures).

**Typical users**:
- Banks: Managing duration mismatch between loan book (often floating) and funding (often fixed)
- Corporates: Converting fixed-rate bond issuance into floating CDI (or vice versa)
- Investment funds: Curve positioning without holding physical bonds

### CDI x IPCA Swaps (Inflação x CDI)

- **Paying leg**: CDI (accumulated, floating)
- **Receiving leg**: IPCA + spread (accumulated inflation plus fixed real spread)

**Use cases**:
- Pension funds: Match IPCA-linked liabilities (actuarial obligations indexed to inflation) without buying physical NTN-B bonds
- Corporates with IPCA-indexed revenues (e.g., toll road concessionaires with IPCA tariff adjustments) can hedge their real rate exposure
- Expressing views on breakeven inflation (IPCA implied by the real rate vs. nominal rate)

**Breakeven inflation via swaps**: The breakeven IPCA implied by CDI x IPCA swap rates versus pre-fixed DI futures is a clean measure of market inflation expectations, free from the liquidity premium embedded in physical bond spreads.

### Cross-Currency Swaps (CCS)

Cross-currency swaps in Brazil involve exchanging principal and interest cash flows between BRL and another currency (usually USD). Structure:

- **Leg 1**: BRL CDI (floating) on BRL notional
- **Leg 2**: USD SOFR + spread (floating) on USD notional, with FX conversion at agreed rate

**Use cases**:
- Foreign companies with BRL debt issuing USD bonds: Use CCS to convert USD coupon obligation into BRL CDI obligation, matching their Brazilian cash flows
- Brazilian companies with USD revenues: Convert USD obligations into BRL
- The "cupom cambial" swap: Economically equivalent to forward FX contracts; used by exporters to lock in future USD/BRL exchange

### Differential Swaps (Swap Cambial)

A unique Brazilian product: Pays CDI, receives change in USD/BRL + USD interest rate (cupom cambial). Economically equivalent to a forward USD purchase. The BCB itself issues **swaps cambiais** in the futures market as its primary FX intervention tool, selling the USD risk (receiving BRL CDI, paying USD exchange rate change), which has the effect of providing USD hedges to the market and supporting BRL.

---

## 9. Forward Contracts (NDF and Termo) {#forward-contracts}

### NDF (Non-Deliverable Forward)

Brazil's capital account restrictions and the offshore nature of many FX transactions make NDFs important. An NDF is a cash-settled forward contract where:

- Two parties agree on a forward exchange rate
- At maturity, the difference between the agreed rate and the prevailing spot rate (typically PTAX) is paid in USD offshore
- No physical BRL delivery occurs

**Key distinction**: NDFs trade offshore (New York, London, Hong Kong) and settle in USD. They allow foreign investors to gain or hedge BRL exposure without holding BRL onshore. The offshore NDF market in BRL is liquid for tenors from 1 week to 2 years.

**Onshore vs. offshore basis**: The NDF rate offshore may differ from the equivalent onshore B3 dollar futures rate due to capital flow restrictions and the cost of accessing the onshore market. This basis (NDF-onshore basis) is monitored by FX desks.

### Termo de Ações (Equity Forward)

The "termo" is an equity forward contract on B3:

- Two parties agree to buy/sell a specific number of shares at a fixed future price
- Standard tenors: 12 to 999 business days
- Settlement: Physical delivery (shares) or financial

**Practical use**: Provides leverage (buyer pays only a margin, not the full stock price) and is used for tax-efficient stock purchases in some structures. Also used by banks to provide structured leverage to clients (client "buys" shares via termo, bank funds the position).

---

## 10. B3 Clearing and Settlement Architecture {#b3-clearing}

### B3 as Central Counterparty (CCP)

B3 operates as the central counterparty for all exchange-traded derivatives and for guaranteed OTC derivatives. As CCP, B3 becomes the buyer to every seller and the seller to every buyer, eliminating bilateral counterparty risk.

**B3's clearing structure comprises:**
- **B3 Clearinghouse (Câmara de Compensação e Liquidação)**: For equity and corporate bond settlement (T+2)
- **BM&F Clearinghouse**: For derivatives, FX, government bonds (T+0 daily settlement for futures MTM, T+1 or T+2 for physical settlement)

### Multilateral Netting

B3's margin and settlement system aggregates positions across instruments using a portfolio margin methodology. For clearing members with large books, positions in correlated instruments can partially offset margin requirements (e.g., a long DI futures position partially offsets a short NTN-F bond position for margin purposes).

### Default Waterfall

B3 maintains a default waterfall to cover member defaults:
1. **Defaulting member's own margin** (initial + variation margin)
2. **Defaulting member's contribution to the default fund**
3. **B3's own capital contribution** (skin in the game)
4. **Surviving members' default fund contributions** (mutualized)
5. **B3's overall equity capital**

This structure has never been breached in practice, though it was stress-tested in the financial crises of 2008 and 2020.

### Daily Settlement and MTM

Futures positions on B3 are marked to market daily. The daily settlement price (ajuste diário) is determined by B3 at the close of each trading session and can differ slightly from the last traded price (based on B3's weighted average calculation methodology). MTM gains are credited to the margin account and can be withdrawn; MTM losses trigger immediate margin calls that must be met by 12:00 the following trading day.

---

## 11. Margin Requirements and Risk Management {#margin-requirements}

### Types of Margin on B3

**Initial Margin (Margem Inicial)**:
The amount deposited upfront when opening a derivatives position. Calculated using B3's CORE (Closeout Risk Evaluation) methodology, which estimates the maximum 1-day loss with high confidence (typically 99.7% confidence interval over a 1- to 5-day closeout horizon depending on the contract's liquidity).

**Variation Margin (Ajuste Diário)**:
Daily P&L settlement. Unlike many global exchanges where variation margin is separate from initial margin, B3 combines both in the margin account.

**Eligible Margin Collateral**:
- Brazilian government bonds (NTN-B, NTN-F, LTN, LFT) — most common institutional collateral
- BRL cash (earns CDI on the margin account, making it "free" to post for domestic investors)
- Equities (with haircuts, typically 30–50% for individual stocks, lower for BOVA11 ETF)
- USD cash (for FX contracts)
- Letters of guarantee (cartas de fiança) from banks

### CORE Methodology

B3's CORE system models correlated stress scenarios across multiple asset classes simultaneously. It accounts for:
- Volatility of the underlying
- Correlation between positions (offsetting positions reduce total margin)
- Liquidity premium for less liquid contracts
- Jump risk (fat tails)

For institutional clients, **portfolio margin** is available: the total initial margin for a diversified portfolio of derivatives positions is typically less than the sum of individual position margins due to correlation offsets.

### Margin Sizing Examples (Approximate)

| Contract | Approximate Initial Margin per Contract |
|---|---|
| DI Jan26 (short term) | BRL 500 – 1,500 per contract |
| DI Jan30 (long term) | BRL 2,000 – 6,000 per contract |
| DOL (dollar full) | BRL 3,000 – 7,000 per contract |
| WDO (mini dollar) | BRL 600 – 1,400 per contract |
| IND (Ibovespa full) | BRL 15,000 – 35,000 per contract |
| WIN (mini Ibovespa) | BRL 3,000 – 7,000 per contract |

*Note: Margin levels change based on market volatility. B3 reviews and adjusts margins regularly. Check B3's published margin tables for current values.*

---

## 12. Hedging Strategies for Equity Portfolios {#equity-hedging}

### Beta Hedging Using Ibovespa Futures

An equity portfolio manager holding a diversified Brazilian portfolio with a beta of approximately 1.0 relative to the Ibovespa can hedge systematic risk by selling IND or WIN futures.

**Number of contracts to sell:**

N = (Portfolio Value × Beta) / (Index Level × Contract Multiplier)

**Example**: Portfolio of BRL 10 million, beta = 1.1, Ibovespa at 125,000, WIN multiplier = BRL 0.20 per point:

N = (10,000,000 × 1.1) / (125,000 × 0.20) = 11,000,000 / 25,000 = 440 WIN contracts

**Dynamic beta hedging**: As the portfolio's beta changes (due to sector rotation, stock selection, market movements), the hedge ratio must be rebalanced. Rebalancing frequency depends on turnover tolerance and transaction costs.

### Tail Risk Hedging with Index Puts

Buying OTM puts on BOVA11 (the Ibovespa ETF) provides downside protection. Typical structure:
- **Strike**: 90–95% of current level (5–10% OTM)
- **Tenor**: 1–3 months (rolling program)
- **Cost**: 0.5–2.5% of portfolio value per quarter depending on vol level

**Cost-efficient alternatives:**
- **Put spreads**: Buy 95% strike put, sell 80% strike put → reduces premium cost but limits protection to the band
- **Collars on individual positions**: Sell OTM calls on specific holdings to fund put purchases
- **Variance swaps** (OTC): Less common in Brazil but available through large bank dealers; provides pure volatility exposure

### Sector Hedging

For portfolios with significant sector concentration (e.g., heavy in financials, or overweight commodities):
- Short Ibovespa futures + long the desired sector creates an implicit sector tilt hedge
- Some bank dealers offer sector swap baskets (e.g., "long IBrX Financial Index, short Ibovespa") as OTC instruments

---

## 13. FX Hedging for Importers and Exporters {#fx-hedging}

### Exporters: Natural Long USD

Brazilian exporters (commodity companies, manufacturers) receive USD revenue and have BRL costs. They are naturally **long USD**, exposed to loss if BRL appreciates.

**Hedging instruments:**
1. **Dollar futures (DOL/WDO)**: Sell USD futures at B3. Most liquid, transparent, exchange-cleared.
2. **NDF offshore**: Sell USD forward in the offshore NDF market. Useful for non-residents or when onshore market access is restricted.
3. **Export pre-payment (ACC — Adiantamento de Contratos de Câmbio)**: Exporter receives BRL upfront from the bank in exchange for future USD receivables. Not a derivative, but achieves FX conversion in advance.
4. **Swap cambial**: Receive BRL CDI, pay USD + FX change. Economically equivalent to selling USD forward.

**Typical export hedge program:**
- Soy farmers typically sell 30–50% of expected harvest via dollar futures or ACC during the pre-planting and growing season (September–February for second crop; December–March for first crop)
- The hedge ratio is determined by the farmer's cost structure (what BRL/USD rate makes the crop economically viable given local costs)
- Breakeven analysis for Mato Grosso soybean farmers in 2024: typically BRL 5.20–5.60/USD plus CBOT soy at ~USD 400/metric ton or higher

### Importers: Natural Short USD

Importers (retailers, manufacturers relying on imported inputs, pharmaceutical companies) have USD liabilities and BRL revenues. They are naturally **short USD**, exposed to loss if BRL depreciates.

**Hedging instruments:**
1. **Dollar futures (DOL/WDO)**: Buy USD futures at B3. Standard hedge.
2. **NDF**: Buy USD forward offshore.
3. **Swap cambial**: Pay BRL CDI, receive USD + FX change.
4. **Standby letter of credit with FX lock**: Banks offer products that lock in the FX rate at the time of importing goods.

**Partial hedging rationale**: Many Brazilian companies hedge only 50–70% of their FX exposure to maintain flexibility and because BRL movements are difficult to forecast. Full hedging of all future USD cash flows at current rates may lock in unfavorable rates during structural BRL overvaluation periods.

### Cross-Hedge for Commodity Producers

A soybean farmer in Brazil faces two distinct price risks:
1. **CBOT soy price risk** (global commodity price, quoted in USD/bushel)
2. **BRL/USD exchange rate risk**

Hedging both requires separate instruments:
- Sell CBOT soy futures (on CME) or B3 SFI futures for commodity price hedge
- Sell dollar futures (WDO/DOL on B3) for FX hedge

The combined position locks in the BRL/sack equivalent revenue. This is a standard agribusiness treasury management practice in Brazil.

---

## 14. Using DI Futures to Manage Interest Rate Risk {#di-hedging}

### Duration Management for Fixed Income Portfolios

A Brazilian fixed income fund holding a portfolio of NTN-F bonds (pre-fixed government bonds maturing in 2027 and 2031) is exposed to DI curve movements. If DI rates rise, bond prices fall (negative MTM).

To reduce duration using DI futures:

**Step 1: Calculate portfolio dollar duration (DV01)**
DV01 = Portfolio Value × Modified Duration × 0.0001

**Step 2: Calculate DV01 per DI futures contract**
DV01_futures = PU × (n/252) / (1 + rate)^(n/252) × 0.0001 × BRL multiplier

**Step 3: Number of contracts to sell**
N = Portfolio_DV01 / DV01_per_contract

**Practical example**: A fund has BRL 100 million in NTN-F 2031 with modified duration of 4.5 years. DV01 = BRL 100mm × 4.5 × 0.0001 = BRL 45,000. If the DI Jan31 contract has a DV01 of approximately BRL 35 per contract at current rates, the hedge requires selling approximately 45,000/35 ≈ 1,285 DI Jan31 contracts.

### Butterfly Trades on the DI Curve

Sophisticated fixed income managers use "butterfly" strategies on the DI curve to profit from changes in curve shape:
- **Positive butterfly (barbell)**: Long short-end DI + long long-end DI, short medium-term DI. Profits if the curve humps (belly cheapens relative to wings).
- **Negative butterfly (bullet)**: Long medium-term DI, short short-end + long-end DI. Profits if the belly richens.

These are executed using combinations of DI futures at different expiries and are the standard toolkit for Brazilian fixed income relative value traders.

### Swaption Market

Brazil has a nascent OTC swaption market (options on interest rate swaps). Liquidity is limited to major bank dealers and is primarily used by large institutional investors to hedge cap/floor structures on floating-rate loans or to create structured note payoffs. Not accessible to most retail or mid-tier institutional investors.

---

## 15. Basis Risk {#basis-risk}

### Definition and Sources in Brazilian Markets

Basis risk is the risk that the hedge instrument and the hedged position do not move in perfect lockstep. In Brazilian markets, major basis risks include:

**1. CDI vs. Specific Funding Rate Basis**
Banks fund themselves using CDBs, LCAs, LCIs, and debentures, which pay CDI + spread or IPCA + spread. Hedging with DI futures (which reflect pure CDI) leaves the spread component unhedged. If credit spreads widen (as in a financial stress scenario), the bank's funding cost rises even if the DI rate is unchanged.

**2. CBOT vs. B3 Commodity Basis**
The price of soybeans on B3's SFI contract reflects the Brazilian port price (FOB Paranaguá or Santos), which equals the CBOT price adjusted for:
- BRL/USD exchange rate (embedded in the B3 price)
- Ocean freight from Brazil to China
- Port handling and logistics costs
- Quality differentials (Brazilian vs. US protein content)

This "basis" between CBOT and B3 SFI is volatile and can swing by USD 10–30/metric ton. A farmer who hedges on CBOT but sells physical grain in Brazil bears this basis risk.

**3. Ibovespa Futures vs. Portfolio Beta Basis**
A portfolio with beta = 1.0 relative to Ibovespa may have tracking error vs. the index due to individual stock weights, sector tilts, and style factors. The Ibovespa futures hedge eliminates systematic risk but not idiosyncratic or factor-specific risk.

**4. PTAX vs. Intraday Spot Rate Basis**
FX derivatives settle at PTAX (morning average). A company with FX exposure that materializes in the afternoon (e.g., a payment due at 3 PM) bears intraday PTAX basis risk.

### Managing Basis Risk

- Use the most correlated available instrument (DI futures for BRL fixed income, CBOT + B3 DOL for soy, BOVA11 puts for equity)
- Accept some residual basis risk as the cost of liquid, exchange-cleared hedging vs. perfect OTC customization
- Monitor basis levels and establish basis bands outside which the hedge should be re-evaluated

---

## 16. Roll Strategies {#roll-strategies}

### Why Rolling Is Necessary

Most Brazilian derivatives contracts are listed for near-term maturities. Investors seeking persistent long or short exposure must "roll" expiring contracts into the next available maturity. The roll creates:

1. **Roll cost or roll yield**: The difference in price between the expiring contract and the next contract
2. **Basis change**: As a new front-month becomes the reference, its basis to spot may differ
3. **Liquidity transition**: Near-month contracts are most liquid; rolling early or late affects transaction costs

### DI Futures Roll Dynamics

DI futures roll the last business day of the month preceding expiry. Key considerations:
- The roll involves simultaneously closing the front-month DI and opening the back-month DI
- If the curve is upward sloping (i.e., further-out rates are higher), rolling a short DI position from near-month to far-month is a "negative roll" (rolling into a higher-rate contract costs money if the curve is steep)
- The professional "spread market" for DI rolls (calendar spread market) is liquid and allows clean roll execution at transparent prices

### Dollar Futures Roll Dynamics

DOL/WDO futures roll monthly. The roll cost is embedded in the cupom cambial structure:
- If the cupom cambial is positive (normal condition: BRL yields exceed USD yields), rolling a short USD position forward costs money — you sell the expiring near-month at a higher price and buy the next month at an even higher price (reflecting the interest rate differential)
- An exporter who perpetually sells dollar futures forward is paying this roll cost implicitly as the "cost of carry" of maintaining a BRL/USD short hedge

### Ibovespa Futures Roll

Ibovespa futures expire every two months (February, April, June, August, October, December). Active roll period is typically 5–10 business days before expiry. The roll cost equals:
- Cost of carry = CDI over the next 2 months minus dividend yield over the next 2 months
- Since CDI > dividend yield in most environments, rolling a long Ibovespa position forward is negative carry (you buy the next contract at a discount, but the discount is less than the CDI you earned on your cash, so it is still costly relative to just holding shares)

---

## 17. Contango vs. Backwardation in Brazilian Commodity Markets {#contango-backwardation}

### Theory Review

**Contango**: Futures price > spot price. Typical when:
- Storage costs are positive
- Carry cost (interest rate × spot price) exceeds convenience yield and dividend/coupon
- No current supply shortage

**Backwardation**: Futures price < spot price. Typical when:
- Current demand exceeds current supply (spot shortage)
- Convenience yield is high (buyers value immediate delivery)
- Supply disruption concerns dominate

### Brazilian Commodity Markets: Specific Dynamics

**Live Cattle (BGI)**:
Brazilian cattle futures are structurally affected by:
- Seasonal slaughter patterns (more cattle go to slaughter in dry season when pasture quality declines)
- Export demand (China's food safety protocols can temporarily disrupt access)
- The "boi gordo" basis to CME live cattle is driven by currency, import tariffs, and Brazilian local supply

BGI futures typically trade in mild contango reflecting cattle financing costs, but can shift to backwardation during domestic supply squeezes.

**Arabica Coffee (ICF)**:
B3 arabica coffee futures trade in relation to ICE (New York) C contract. Key drivers:
- Brazilian harvest cycle (May–September): Contango often occurs post-harvest as fresh supply enters
- Frost risk in Paraná and São Paulo (July–August): Frost events can cause sharp backwardation as spot prices spike
- The differential between B3 ICF and ICE C reflects shipping costs, quality premiums for Brazilian naturals, and local supply/demand

**Ethanol (ACF)**:
Anhydrous ethanol futures on B3 reflect:
- Cane harvest season (April–November in Center-South Brazil)
- Pre-harvest: Typically backwardation (current ethanol stocks low, demand for blending)
- Post-harvest: Contango (production fills storage, lower spot prices)
- Sugar price parity: When sugar is more profitable than ethanol for mills, production shifts to sugar, reducing ethanol supply

---

## 18. Regulatory Framework {#regulatory-framework}

### Principal Regulators

**CMN (Conselho Monetário Nacional)**:
Brazil's supreme monetary and financial policy authority. Sets broad rules for financial market operation, capital requirements, and derivative usage by regulated entities (banks, investment funds). CMN resolutions are legally binding on all regulated institutions.

**BCB (Banco Central do Brasil)**:
Regulates and supervises banks and financial institutions (bancos múltiplos, bancos comerciais, financeiras). For derivatives, the BCB:
- Regulates FX derivatives (all contracts involving BRL/foreign currency exchange)
- Requires registration of FX derivatives in B3 (formerly Cetip) regardless of whether exchange-traded or OTC
- Sets capital requirements for banks' derivatives books (following Basel III framework, adapted for Brazil by the BCB's own circulars)
- Issues BCB Resolutions and Circulars governing FX market access

**CVM (Comissão de Valores Mobiliários)**:
Brazil's securities regulator (equivalent to the SEC in the US). Regulates:
- Investment funds (FIFs, FIAs, FIDCs, FIPs) and their use of derivatives
- Broker-dealers and investment banks in their capital market activities
- Listed company disclosures of derivative positions (DFPs, FREs)
- CVM Instruction 555 (now Resolution 175) governs investment fund operations, including derivatives limits and disclosure requirements

**B3 as Self-Regulatory Organization (SRO)**:
B3 acts as a first-level regulator for its own members, establishing trading rules, margin requirements, position limits, and market surveillance. B3's BSM (B3 Supervisão de Mercados) conducts market surveillance and refers cases to CVM/BCB.

### Key Regulatory Rules for Derivatives

**Position Limits**: B3 sets position limits for commodity futures (particularly live cattle, arabica coffee) to prevent market manipulation. Position limits are expressed as maximum percentage of open interest per client.

**EMIR-equivalent registration**: All OTC derivatives between regulated entities must be registered in B3's trade repository (Sistema de Registro da B3). This provides the BCB and CVM with systemic risk surveillance data.

**Foreign Investor FX Derivatives**: Foreign investors accessing Brazilian markets under Resolution CMN 4,373 (now superseded by Resolution 4,852 and subsequent regulations) may use dollar futures and swaps for hedging their Brazilian investments without restriction. Speculative FX positions by foreign investors are permitted but subject to position reporting.

**Investment Fund Derivative Limits (CVM Resolution 175)**:
- Equity funds (FIA): May use derivatives for hedging and limited speculative purposes
- Fixed income funds: May use DI, dollar, and interest rate derivatives; leverage limits apply
- Multimarket funds (FIM): Most flexible; may use all derivative types with no explicit notional limit beyond risk management rules
- "Alavancagem" (leverage) disclosure required if fund's derivative exposure exceeds NAV

---

## 19. Taxation of Derivatives {#taxation}

### General Principle: Income Tax on Gains

Derivative gains are generally subject to income tax (IR) in Brazil. The applicable rate and withholding mechanism depend on:
1. Whether the investor is a resident (pessoa física or pessoa jurídica) or non-resident
2. Whether the derivative is exchange-traded or OTC
3. Whether the position is classified as hedging or speculation
4. The holding period (in some cases)

### Brazilian Individuals (Pessoa Física)

| Contract Type | Tax Rate | Collection Method |
|---|---|---|
| Exchange-traded derivatives (B3) | 15% on net gains per month | Self-reported DARF monthly |
| OTC derivatives | 15% on net gains | Withholding by financial institution |
| Options with exercise | 15% (gains treated as equity gains if on stocks) | Self-reported |
| Day trade (exchange-traded) | 20% | Withholding at source (0.005%) + top-up via DARF |

**Key rule for individuals**: Gains from exchange-traded derivatives in a given month can be offset by losses in the same month across all exchange-traded derivative positions. Losses cannot be carried back, but can be carried forward to offset future gains from the same category.

**Dividend-like structures**: Gains from some structured products involving derivatives may be reclassified as interest (JCP — Juros sobre Capital Próprio) and taxed at 15% at source.

### Brazilian Legal Entities (Pessoa Jurídica)

Corporate taxpayers (IRPJ + CSLL) include derivative gains in taxable income:
- IRPJ: 15% basic rate + 10% surtax on income above BRL 20,000/month = effective 25%
- CSLL: 9% (financial institutions: 15%)
- Gains and losses from derivatives are generally included in monthly estimated tax (ESTIMATIVA) calculations

**Hedge accounting**: Under Brazilian GAAP (CPC 38/48, aligned with IFRS 9), companies designating derivatives as accounting hedges can record gains/losses against the hedged item rather than immediately in P&L. This requires formal hedge documentation, effectiveness testing, and designation at inception.

### Foreign Investors (Não-Residentes)

Non-resident investors operating under CMN Resolution 4,852 benefit from **preferential tax treatment on DI futures and OTC fixed income derivatives**:

- **DI futures and interest rate derivatives**: 0% tax on gains (the "zeragem" for foreign investors in interest rate futures was introduced to attract foreign participation in the local interest rate curve)
- **FX derivatives (dollar futures)**: 0% (aligned with the treatment of FX spot transactions)
- **Equity derivatives (Ibovespa futures, equity options)**: 15% standard rate, same as residents; exemption applies only if the equity derivative qualifies under the same rules as equity investments (which receive 0% under current rules for portfolio investments by non-residents meeting specific criteria)

**IOF on derivatives**: The IOF (Imposto sobre Operações Financeiras) may apply at 0% or higher rates depending on the nature of the operation. For most derivative transactions between financial institutions, IOF is 0%.

---

## 20. Institutional vs. Retail Use Cases {#institutional-vs-retail}

### Institutional Investor Use Cases

**Commercial Banks (Treasury Desks)**:
- ALM (Asset-Liability Management): DI futures and swaps to match duration of loan book vs. deposit funding
- FX hedging: Dollar futures for trade finance and corporate client FX risk
- Proprietary trading: DI curve strategies, cross-asset macro positions

**Pension Funds (Entidades Fechadas de Previdência Complementar — EFPCs)**:
- ALM hedging: NTN-B-linked swaps to match INPC/IPCA liability indexation
- IPCA swaps: Receive IPCA + spread, pay CDI — creates synthetic NTN-B exposure without holding physical bonds
- Duration extension: DI futures to adjust portfolio duration within regulatory limits (Resolução CMN 4,994)
- Equity overlay: Ibovespa futures for beta management and cash equitization

**Insurance Companies (Seguradoras)**:
- Match policy liabilities (often long-duration, IPCA-linked) with appropriate assets
- Use CDI x IPCA swaps to convert CDI-paying CDB assets into IPCA-equivalent for liability matching
- Regulated by SUSEP; CMN Resolution 4,994 governs investment limits for insurance technical reserves

**Investment Funds (Fundos Multimercado)**:
Multimercado funds are the primary speculative users of derivatives in Brazil. They employ:
- DI curve positioning (long/short different tenors)
- BRL/USD directional positioning
- Cross-asset macro strategies (long Ibovespa + short DI, etc.)
- Offshore derivatives via offshore vehicles (BDRs, offshore FX, CME commodity futures)

**Non-Financial Corporates**:
- Exporters: Systematic dollar futures selling programs (hedge production revenue)
- Importers: Dollar futures buying programs (hedge import costs)
- Infrastructure concessionaires: IPCA swaps to hedge inflation-linked tariff revenue against fixed-cost obligations
- Debt management: Interest rate swaps to convert between fixed and floating rate obligations

### Retail Investor Use Cases

Retail access to derivatives on B3 is primarily through:

**Mini contracts (WIN, WDO)**: Low notional per contract (Ibovespa mini = ~BRL 25,000 exposure at Ibovespa 125,000; mini dollar = USD 10,000 = ~BRL 50,000 exposure). Popular among individual day traders ("day traders" in Brazilian slang).

**Equity options (lançamento coberto)**: Covered call writing is the most common retail options strategy. A retail investor holding PETR4 or VALE3 sells call options monthly to generate income, effectively treating the option premium as additional "dividend." This strategy is viable when implied volatility is elevated (premium is high relative to the probability of exercise).

**Structured products**: Banks offer capital-protected notes and yield enhancement products to retail HNW clients using embedded derivatives. These are sold through private banking channels and are not exchange-traded.

**Important suitability note for advisors**: Retail investors using leverage through derivatives (particularly mini dollar or Ibovespa mini futures with day-trading strategies) face high risk of loss. CVM regulations require suitability assessments; leveraged derivatives are generally classified as "agressivo" on the CVM API (perfil de risco) scale and should not be sold to conservative or moderate clients.

---

## 21. Practical Reference Tables {#reference-tables}

### Key Brazilian Derivatives at a Glance

| Contract | Code | Exchange | Underlying | Contract Size | Most Liquid Tenors |
|---|---|---|---|---|---|
| DI Futures (full) | DI1 | B3 | Accumulated CDI | BRL 100,000 notional | Up to 5 years, monthly |
| Dollar Futures (full) | DOL | B3 | BRL/USD | USD 50,000 | Up to 12 months, monthly |
| Dollar Futures (mini) | WDO | B3 | BRL/USD | USD 10,000 | Up to 6 months |
| Ibovespa Futures (full) | IND | B3 | Ibovespa | BRL 1/pt | Bimonthly, up to 1 year |
| Ibovespa Futures (mini) | WIN | B3 | Ibovespa | BRL 0.20/pt | Bimonthly |
| Ibovespa Options | OI | B3 | Ibovespa Futures | Same as IND | Monthly |
| PETR4 Options | PETR4C/P | B3 | PETR4 shares | 100 shares/contract | Monthly |
| VALE3 Options | VALE3C/P | B3 | VALE3 shares | 100 shares/contract | Monthly |
| Live Cattle Futures | BGI | B3 | Boi gordo (330 @) | 330 arrobas | Monthly |
| Arabica Coffee | ICF | B3 | Coffee (60-kg bags) | 100 bags | Bimonthly |
| Ethanol Anhydrous | ACF | B3 | Ethanol (m³) | 30 m³ | Monthly |

### Common Hedging Structures Quick Reference

| Risk Exposure | Hedging Instrument | Position | Settlement |
|---|---|---|---|
| Rising BRL interest rates (long bonds) | DI Futures | Short (sell) | B3, financial |
| Falling BRL (long BRL assets) | Dollar Futures | Buy USD futures | B3, PTAX |
| Rising BRL (USD exporter) | Dollar Futures | Sell USD futures | B3, PTAX |
| Ibovespa market decline | Ibovespa Futures or BOVA11 puts | Short IND/WIN or Buy puts | B3, financial |
| Rising inflation (IPCA) | NTN-B bonds or CDI x IPCA swap | Buy NTN-B / Receive IPCA | B3 / OTC |
| Falling Selic (long floating assets) | DI Futures | Buy (long in rate terms = sell PU) | B3, financial |

### Key B3 Settlement Dates 2025 (Illustrative)

DI futures expire on the first business day of each calendar month. Dollar and Ibovespa futures expire:
- Dollar futures: First business day of each month
- Ibovespa futures: Wednesday nearest to the 15th of February, April, June, August, October, December

Advisors and portfolio managers should maintain a derivatives expiry calendar to manage roll timing and avoid assignment/exercise surprises.

---

*This document is prepared by the Decade Investment Research team for internal distribution to advisors and qualified investors. It provides a reference framework for understanding Brazilian derivatives markets and does not constitute investment advice for any specific client. Derivatives involve leverage and the risk of loss that may exceed the initial investment. All regulatory references are current as of early 2025; regulatory frameworks evolve and advisors should verify current rules with compliance prior to client recommendations. Past performance is not indicative of future results.*

---

**Decade Investment Research**
*Conviction | Clarity | Consistency*

---

## Advanced Topics and Extended Reference

---

## 22. Detailed Worked Examples of Common Hedging Strategies {#worked-examples}

### 22.1 Exporter Hedge: Soybean Farmer in Mato Grosso

**Scenario**: A large soybean producer in Lucas do Rio Verde, Mato Grosso expects to harvest 200,000 bags (3,000 metric tons) of soybeans in March 2025. The crop was planted in October 2024. In November 2024, the following market conditions prevail:

- CBOT March 2025 soybean futures: USD 12.50 / bushel
- B3 WDO (mini dollar) March 2025 futures: BRL 5.15 / USD
- Implied BRL equivalent: ~BRL 122.50 / 60-kg bag (using standard conversion: 1 bushel = 27.216 kg, so 60 kg = 2.204 bushels; 2.204 × USD 12.50 × BRL 5.15 / USD = BRL 141.88 / bag gross, before basis and freight adjustments)
- Local cash basis (Paranaguá port differential): -USD 0.50 / bushel
- Local port costs and freight from farm to port: BRL 18 / bag
- Production cost on farm: BRL 95 / bag

**Break-even analysis**:
- Revenue per bag: BRL 141.88 - (BRL 0.50 × 2.204 × BRL 5.15) - BRL 18 = BRL 141.88 - BRL 5.68 - BRL 18.00 = **BRL 118.20 / bag**
- Production cost: BRL 95 / bag
- Gross margin per bag: BRL 23.20
- Total gross margin for 200,000 bags: **BRL 4.64 million**

**The farmer decides to hedge 100% of the crop** (considered aggressive but common for risk-averse producers with significant debt):

**Step 1: Hedge commodity price risk via CBOT**
- Sell 550 CBOT March 2025 soybean futures contracts (each contract = 5,000 bushels; 3,000 MT ÷ 27.216 kg/bushel ÷ 5,000 bushels = 110,231 bushels ÷ 5,000 = 22 contracts, but the farm typically over-hedges on CBOT; assume 22 contracts for 3,000 MT of physical)
- Sell 22 CBOT March 2025 soybean contracts at USD 12.50 / bushel

**Step 2: Hedge FX risk via B3 dollar futures**
- Expected USD revenue from 3,000 MT of soybeans: 3,000 MT × 1,000 kg/MT ÷ 27.216 kg/bushel × USD 12.50/bushel = 1,100,000 bushels × USD 12.50 = USD 13.75 million (gross, before costs)
- Net USD revenue after port costs (paid in BRL): approximately USD 12 million
- Sell 1,200 WDO March 2025 contracts (each = USD 10,000) at BRL 5.15 / USD

**Outcome 1 — BRL depreciates to 5.80 / USD, CBOT stable at USD 12.50**:
- Physical soybeans sell locally at BRL 5.80 × USD 12.00 = BRL 69.60 (simplified per USD)
- WDO futures gain: (5.80 - 5.15) × USD 10,000 × 1,200 contracts = BRL 0.65 × USD 12 million = BRL 7.8 million gain on WDO
- CBOT futures: no gain/loss (price stable)
- Net position: BRL depreciation captured via futures gain; final BRL revenue protected at approximately original BRL 5.15 level

**Outcome 2 — BRL appreciates to 4.70 / USD, CBOT drops to USD 11.00**:
- WDO futures loss: (5.15 - 4.70) × USD 12 million = BRL 5.4 million loss
- CBOT futures gain: (12.50 - 11.00) × 110,231 bushels = USD 1.65 million = BRL 7.76 million gain (converted at 4.70)
- Combined futures result: gain of BRL 2.36 million
- Physical revenue lower due to lower CBOT price and stronger BRL
- Net: hedge significantly reduced total P&L variance in both scenarios

**Key insight**: The cross-hedge using both CBOT (USD-denominated commodity) and WDO (BRL/USD) futures is essential for Brazilian soybean producers. Hedging only one leg leaves material unhedged risk.

---

### 22.2 Fixed Income Fund: Managing Duration Ahead of a Copom Meeting

**Scenario**: A Brazilian multimarket fund (Fundo Multimercado) manages a BRL 500 million fixed income portfolio. Portfolio composition in December 2024:

| Bond | Notional (BRL mm) | Maturity | Modified Duration | DV01 (BRL) |
|---|---|---|---|---|
| NTN-B 2026 | 150 | Aug-2026 | 1.5 yrs | 22,500 |
| NTN-B 2035 | 200 | May-2035 | 7.2 yrs | 144,000 |
| NTN-F 2031 | 150 | Jan-2031 | 4.8 yrs | 72,000 |
| **Total** | **500** | — | **4.77 yrs** | **238,500** |

The fund manager expects the upcoming Copom meeting to result in a hawkish surprise: market is pricing 50 bps hike, but the manager believes Copom will hike 75 bps and signal further tightening. This implies DI rates across the curve should rise by 25–40 bps beyond what is currently priced.

**Target**: Reduce portfolio DV01 by 60% (from BRL 238,500 to BRL 95,400) using DI futures.

**Calculation**:
- DV01 reduction needed: BRL 238,500 - BRL 95,400 = **BRL 143,100**
- Target DI contracts for hedging: primarily DI Jan2027, DI Jan2031, and DI Jan2036

**For the long-end (NTN-B 2035 hedge)**:
- NTN-B 2035 has 7.2-year modified duration; most correlated DI contract is DI Jan2036 (approximately 9 years to expiry at 9% DI rate → DV01 per contract ≈ BRL 60 at current market)
- Contracts to sell: BRL 144,000 / BRL 60 = 2,400 DI Jan2036 contracts to short

**For the medium-term (NTN-F 2031 hedge)**:
- DI Jan2031 DV01 per contract at current rate (≈ BRL 50 per contract)
- Contracts to sell: BRL 72,000 / BRL 50 = 1,440 DI Jan2031 contracts to short

**For the short-end (NTN-B 2026 partial hedge)**:
- DI Jan2027 DV01 per contract (≈ BRL 25 per contract)
- Contracts to sell: BRL 22,500 / BRL 25 = 900 DI Jan2027 contracts

**Post-hedge portfolio DV01**: approximately zero (full hedge) or reduced as desired

**Copom result**: Copom hikes 75 bps (hawkish surprise). DI curve shifts up 25 bps beyond previous market pricing.

**P&L from futures positions**:
- DI Jan2036 short: gain of 25 bps × DV01 × 2,400 contracts × BRL 60 / bps = BRL 3.6 million gain
- DI Jan2031 short: gain of 25 bps × BRL 50 × 1,440 = BRL 1.8 million gain
- DI Jan2027 short: gain of 25 bps × BRL 25 × 900 = BRL 562,500 gain
- **Total futures gain: approximately BRL 5.96 million**

**Physical bond portfolio loss**:
- DV01 × 25 bps × notional factor = BRL 238,500 × 25 = BRL 5.96 million loss (approximately, before convexity adjustment)

**Net result**: Approximately flat P&L. Without the hedge, the fund would have lost ~BRL 5.96 million (approximately 1.2% NAV) on a 25 bps adverse rate move.

---

### 22.3 Corporate FX Hedge: Importer with USD Payable

**Scenario**: A Brazilian pharmaceutical importer (Farmácias São Paulo S.A.) has a USD 30 million payable due in 90 days (March settlement). In December, BRL/USD trades at 5.20. The CFO is concerned BRL will depreciate.

**Available instruments**:
1. B3 DOL futures (full contract, USD 50,000 each): Buy 600 contracts at BRL 5.22 (futures slightly above spot due to carry)
2. NDF (offshore): Buy USD 30 million 90-day NDF at approximately BRL 5.21 (offshore basis)
3. Options collar: Buy USD call at strike BRL 5.40 (protection against severe depreciation), sell USD put at strike BRL 5.00 (cap upside from BRL appreciation). Net premium: approximately zero (zero-cost collar)

**CFO selects DOL futures hedge** due to B3's transparency and lower counterparty risk.

**Trade execution**: Buy 600 DOL March 2025 contracts at BRL 5.22 / USD.

**Margin requirement**: B3 margin on 600 DOL contracts = approximately BRL 3 million initial margin (posted in LFTs or CDBs to minimize opportunity cost).

**Scenario analysis at March settlement**:

| March BRL/USD | Physical cost (BRL) | DOL gain / (loss) | Net cost (BRL) | Effective rate |
|---|---|---|---|---|
| 4.80 | 144,000,000 | (12,600,000) | 131,400,000 | 4.38 |
| 5.00 | 150,000,000 | (6,600,000) | 143,400,000 | 4.78 |
| 5.22 | 156,600,000 | 0 | 156,600,000 | 5.22 |
| 5.50 | 165,000,000 | +16,800,000 | 148,200,000 | 4.94 |
| 5.80 | 174,000,000 | +34,800,000 | 139,200,000 | 4.64 |

Note: the DOL gain/(loss) calculation is (March PTAX - 5.22) × USD 50,000 × 600 contracts. The effective rate shows the total cost locked in. The hedge is not perfect because of the basis between the futures settlement rate and the actual USD payment, but it provides close protection.

**Collar alternative comparison**: The zero-cost collar (buy call at 5.40, sell put at 5.00) provides:
- No upside benefit if BRL appreciates below 5.00 (gives up BRL gains below that level)
- Protection only above 5.40 (participates in BRL depreciation up to 5.40 without coverage)
- Between 5.00 and 5.40: fully exposed to rate movement

For the CFO seeking certainty, the DOL futures hedge is superior to the collar.

---

### 22.4 Covered Call Writing on Petrobras (PETR4)

**Scenario**: An HNW individual investor holds 100,000 PETR4 shares purchased at BRL 28.00. PETR4 currently trades at BRL 36.50. The investor wants to generate additional income while maintaining the position for at least another 6 months.

**Market conditions**: PETR4 30-day implied volatility = 38% annualized. One-month ATM call options with strike BRL 37.00 trade at BRL 1.40 per share.

**Strategy**: Sell 1,000 call option contracts (each = 100 shares = 100,000 shares total) PETR4C370 expiring in 4 weeks at BRL 1.40 / share.

**Income generated**: BRL 1.40 × 100,000 shares = **BRL 140,000** (option premium received). This represents 3.8% of current market value in one month, or approximately 45% annualized — extremely high premium income that reflects PETR4's high implied volatility.

**P&L scenarios at expiry**:

| PETR4 at expiry | Option result | Stock P&L vs. current | Net P&L |
|---|---|---|---|
| 32.00 | Option expires worthless (+BRL 140k) | -450,000 | -310,000 |
| 36.50 | Option expires worthless (+BRL 140k) | 0 | +140,000 |
| 37.00 | Option expires at breakeven (+BRL 140k) | +50,000 | +190,000 |
| 38.40 | Option exercised (-BRL 100k), premium kept (+140k) | +190,000 | +190,000 |
| 42.00 | Option exercised (-500k net loss on call), premium kept (+140k) | +550,000 | +190,000 |

The covered call "caps" the investor's upside at the strike + premium received (BRL 37.00 + BRL 1.40 = BRL 38.40 effective cap). Above BRL 38.40, the investor earns nothing additional from share appreciation. Below BRL 36.50, the investor retains the premium (reducing the loss).

**Tax consideration**: Premium income from covered calls is taxed at 15% (capital gains rate for exchange-traded options). The BRL 140,000 premium generates BRL 21,000 in income tax if no offsetting losses.

---

## 23. Historical Case Studies: Brazilian Derivatives During Market Crises {#historical-case-studies}

### 23.1 The 2008 Global Financial Crisis: Aracruz Celulose and the FX Derivatives Disaster

The 2008 global financial crisis produced the most dramatic derivatives-related corporate disaster in Brazilian history. Aracruz Celulose S.A., then the world's largest producer of bleached eucalyptus pulp, revealed in October 2008 that it had accumulated losses of approximately **BRL 2.13 billion** (approximately USD 1.2 billion at the time) on exotic FX derivatives contracts.

**Background**: Aracruz was a natural USD receiver — it sold pulp in USD globally and had BRL costs. Rather than simply selling USD forward (a conventional hedge), it had entered into "leveraged target redemption forwards" and "barrier options" structured by bank dealers. These structures were marketed as yield-enhancement tools: Aracruz would receive above-market BRL rates as long as USD/BRL stayed within a band (typically BRL 1.70–1.90 / USD, the range of 2006–2008). In exchange, Aracruz was obligated to sell USD at below-market rates or in multiples of its natural production if BRL breached trigger levels.

**The shock**: BRL weakened from approximately BRL 1.60 / USD in July 2008 to BRL 2.40 / USD by late October 2008 — a 50% depreciation in weeks. Aracruz's barrier structures were breached. The company was forced to sell USD at BRL 1.80 while market rates were BRL 2.40, and with leveraged notional multiples, losses compounded rapidly.

**Other corporate casualties**: Sadia S.A. (another major food company, since merged into BRF S.A.) revealed BRL 760 million in similar losses. Together, these were estimated to represent BRL 20–30 billion in system-wide corporate derivative losses, though most were smaller positions.

**Market impact**: The DI curve shifted dramatically in the crisis period. DI futures for 6-month and 1-year tenors spiked as BCB cut rates in late 2008 — counterintuitively, the BCB initially held rates at 13.75% and only began cutting in January 2009. Dollar futures for near-month maturity traded at BRL 2.50+. Open interest in dollar futures fell sharply as risk appetite collapsed.

**Regulatory response**: CVM and BCB jointly issued guidance requiring greater disclosure of OTC derivative positions in annual reports. Companies must now disclose net derivative positions by type, notional values, and sensitivity analysis in annual DFPs (Demonstrações Financeiras Padronizadas).

**Lessons for advisors**: Leveraged structured FX derivatives marketed as "yield enhancement" to natural hedgers carry catastrophic tail risk. The Aracruz/Sadia episode is the canonical case study in Brazilian derivatives risk management failures.

---

### 23.2 The 2015–2016 Brazilian Recession: DI Futures at 14.25%

The 2015–2016 period saw Brazil's worst economic contraction in modern history: GDP fell 3.8% in 2015 and another 3.6% in 2016. The political crisis (Operation Lava Jato, Dilma Rousseff's impeachment) combined with fiscal collapse to produce extreme moves across Brazilian derivatives markets.

**DI Futures trajectory**:

| Date | Selic Rate | DI Jan2017 | DI Jan2021 | Curve Shape |
|---|---|---|---|---|
| Jan 2015 | 12.25% | 13.00% | 13.50% | Slightly inverted at short end |
| Sep 2015 | 14.25% | 14.90% | 15.50% | Flat to slightly upward sloping |
| Dec 2015 | 14.25% | 15.30% | 15.80% | Steep, market pricing further hikes |
| Mar 2016 | 14.25% | 13.80% | 13.50% | Inverted — market pricing future cuts |
| Dec 2016 | 13.75% | 11.00% | 11.50% | Steep downward inversion |

**Key trade that worked**: Buying DI futures (i.e., positioning for rate cuts) when the curve was most inverted in late 2015 / early 2016. The DI Jan2021 contract priced at 15.80% in December 2015 eventually settled reflecting a Selic of approximately 7.00% by mid-2018. A fund that was long BRL 1 billion notional DI Jan2021 from December 2015 captured enormous MTM gains as rates collapsed.

**Dollar futures**: BRL/USD moved from BRL 2.80 in January 2015 to BRL 4.19 in September 2015 (peak depreciation), before recovering to approximately BRL 3.20 by the end of 2016. Exporters who had sold dollar futures in the BRL 2.80–3.00 range experienced enormous margin calls (the WDO mark-to-market loss on a short position as BRL/USD rose to 4.19 was approximately BRL 1.39 / USD — on USD 10 million of hedges, a margin call of BRL 13.9 million). Many smaller exporters were forced to close hedges at inopportune moments.

**Ibovespa options**: Implied volatility on Ibovespa options spiked to 35–45% in 2015 (from 15–20% in calm periods). Put options became extremely expensive. Managers who had pre-purchased protection (Ibovespa puts) saw enormous gains as the index fell from 55,000 to below 40,000. The cost of this protection in hindsight was minimal — 3-month 10% OTM puts at 20% implied vol cost approximately 50–80 bps of portfolio NAV, and with vol spiking to 40%+ and the index falling 25%+, these puts paid 5–15x.

---

### 23.3 The 2020 COVID-19 Shock: Circuit Breakers and the Selic at 2%

March 2020 was the most volatile month in Brazilian financial market history. The Ibovespa triggered B3's circuit breakers (15-minute trading halts at -10% daily moves) on multiple occasions. BRL/USD reached BRL 5.74 — a historic low for the currency. The BCB cut the Selic from 4.25% to an eventual 2.00% by August 2020.

**Derivatives market dynamics**:

**Dollar futures (DOL/WDO)**:
- Open interest in WDO reached record highs as both hedgers and speculators rushed to buy USD
- The near-month WDO March 2020 contract gapped from approximately BRL 4.40 to BRL 5.50 in the space of two weeks
- Margin calls from B3 on short USD positions (exporters and macro funds that had been short USD expecting BRL stability) were enormous: estimated at BRL 40–60 billion system-wide across the March–April period
- BCB announced USD 60 billion in reserve swap auctions to provide USD liquidity to the market, stabilizing the DOL spread vs. offshore NDF

**DI Futures**:
- The DI curve initially steepened sharply as the market priced fiscal uncertainty (emergency spending by the government without a clear fiscal framework), even as BCB began cutting rates
- DI Jan2022 briefly reached 6.50% even as BCB signaled aggressive cuts — the market was demanding a fiscal risk premium over and above the expected Selic path
- After the BCB cut to 3.75% in April 2020, the entire DI curve shifted down rapidly. Funds that held long DI positions (positioned for rate cuts) made extraordinary gains

**Ibovespa options**:
- VIX analog for Brazil (IVOL-B3) spiked to all-time highs of 80–90% implied volatility in March 2020
- The Ibovespa fell from 119,000 in February 2020 to 63,500 in March 2020 (-47% in weeks)
- Protective puts purchased by institutional funds performed extremely well; conversely, covered call writers who had sold calls were relatively protected on the downside but had surrendered upside
- When the Ibovespa recovered to 125,000+ by end 2020, investors who had used the March lows to sell short-dated puts (using high implied vol to generate income) or buy deeply OTM calls captured asymmetric gains

**Liquidity management lesson**: Many funds that held Ibovespa short positions through futures faced severe margin pressure simultaneously with BRL depreciation pressure (if also short BRL). B3's margin requirements dynamically increased as vol spiked, creating liquidity spirals for some leveraged funds.

---

### 23.4 The 2022 Lula Election: Political Risk Premia in DI and BRL

The October 2022 Brazilian presidential election — a closely contested race between incumbent Jair Bolsonaro and former President Luiz Inácio Lula da Silva — produced significant volatility in derivatives markets in the weeks before and after the result.

**Pre-election positioning (September–October 2022)**:
- DI curve: Markets priced significant political risk premium. DI Jan2029 traded at approximately 13.20%, implying a real rate of approximately 6.5–7% — substantially above historical neutral real rate estimates of 4–5%. The "fiscal uncertainty" premium was embedded in long-dated DI.
- BRL/USD: The real had depreciated from approximately BRL 5.15 at the start of 2022 to BRL 5.40 by election day, with significant intraday volatility (± BRL 0.30 in a single session on polling day)
- Ibovespa: Trading near 118,000 but with elevated put-call skew — investors were paying up for downside protection in the 10–15% OTM range

**First round result (October 2, 2022 — inconclusive)**:
- Lula received ~48.4%, Bolsonaro ~43.2%. Neither crossed 50%: runoff required
- Initial market reaction: mild relief that it was not a decisive Lula victory, BRL appreciated slightly to BRL 5.20

**Second round result (October 30, 2022 — Lula wins)**:
- Lula won with approximately 50.9% of the vote
- BRL/USD: Moved from BRL 5.30 pre-result to approximately BRL 5.65 in the week following the election as markets priced fiscal risk
- DI futures: Long-end (DI Jan2027, Jan2029) rose 30–50 bps on concern about Lula's stated intentions to loosen fiscal rules
- Ibovespa: Fell approximately 5% in the days following the election, driven by financials and domestics; commodity names more resilient as commodity prices remained firm

**The December 2022 PEC da Transição shock**:
- Lula's transition team proposed a "PEC da Transição" (constitutional amendment) to spend BRL 175 billion above the spending cap in 2023 for social programs
- This triggered the most violent single-day DI curve move of the year: DI Jan2027 rose 80 bps intraday on the announcement date (December 7, 2022)
- BRL/USD jumped from BRL 5.30 to BRL 5.50 in a day; 1-week WDO options with delta = 0.10 (far OTM) tripled in premium

**Lessons for derivatives users**: Brazilian elections generate option vol spikes that make buying protective positions expensive in advance. The pattern of "expensive pre-election protection" has historically made selling vol into elections an attractive strategy — but the December 2022 PEC shock showed that the political risk often extends well beyond election day itself.

---

## 24. Exotic Derivatives in the Brazilian Context {#exotic-derivatives}

### 24.1 Barrier Options

Barrier options are path-dependent options where the payoff is conditional on the underlying asset reaching a specified price level (the "barrier") during the option's life. They are less common on B3's listed market but widely traded OTC by banks for corporate clients.

**Types used in Brazil**:

**Down-and-out puts (Knock-out puts)**: A put option that is extinguished if the underlying falls to the barrier. Used by funds that want equity downside protection but believe a massive collapse is unlikely. Cheaper than vanilla puts because the protection disappears in the most extreme scenarios.

- Example: A fund holds Ibovespa exposure and buys a 6-month put with strike 115,000 (current index = 120,000) and a knock-out barrier at 95,000 (assumes protection not needed if market crashes that far). Premium: 60% cheaper than a vanilla 115,000 strike put. Trade-off: in a genuine crash (Ibovespa falls to 90,000), the put is extinguished and provides zero protection.

**Up-and-in calls (Knock-in calls)**: A call option that only activates if the underlying rises to the barrier. Used speculatively or by structured product desks.

**Barrier options on BRL/USD** are the most common OTC exotics in Brazil. Bank treasurers for exporters and importers use them to reduce hedging costs:

- **Down-and-out USD call with barrier at BRL 4.50**: An importer buys a USD call (protection against BRL depreciation) at BRL 5.50 strike, which is extinguished if BRL appreciates below BRL 4.50. Cost: approximately 40% cheaper than vanilla USD call. The importer accepts that in a scenario of extreme BRL strength (below 4.50), they do not need the hedge anyway (their costs are lower in that scenario).

**Aracruz 2008 revisited**: The structures that destroyed Aracruz were variations of barrier options with leverage. The bank-designed products included "double knock-out" features where Aracruz received a high premium on normal conditions but was obligated to sell USD at locked prices if barriers were breached — and with notional multipliers of 2x or 3x. This amplified losses catastrophically.

**Current regulatory safeguards**: Post-2008, the BCB requires banks to conduct formal suitability assessments before selling complex derivatives (including barriers and exotic structures) to non-financial clients. Banks must demonstrate the client understands the maximum possible loss.

### 24.2 Asian Options (Average-Price Options)

Asian options pay based on the average price of the underlying over the life of the option, rather than the terminal price. They are particularly relevant for:

- **Commodity producers**: A soybean farmer's actual revenue is the average of prices received over the harvest period (March–May), not any single price. An Asian option on the average CBOT price over March–May more closely matches the actual hedging need than a European option on any single maturity date.
- **FX exposure with recurring cash flows**: A multinational corporation with monthly USD receivables over a year can use a 12-month average-price USD put to hedge the average BRL/USD rate received across all monthly conversions. This is typically cheaper than a strip of 12 monthly European options because the average smooths out individual monthly volatility.

**Pricing dynamics**: Asian options are generally cheaper than equivalent vanilla options because the average has lower variance than the terminal price (variance of an arithmetic average over T observations is proportional to 1/T times the variance of the terminal value, approximately).

**Brazilian market specifics**: Asian options on BRL/USD are offered by major Brazilian bank dealers (Itaú BBA, Bradesco BBI, BTG Pactual) to corporate clients. They are documented under ISDA Master Agreements (international standard) with Brazilian law governing for domestic entities. The PTAX-based settlement is most common.

### 24.3 Variance Swaps

A variance swap is an OTC contract that pays the difference between realized variance and the fixed (strike) variance agreed at inception. The buyer of a variance swap profits if realized volatility exceeds the implied volatility (strike) at the time of execution.

**Formula**: Payoff = Notional × (Realized_Variance - Strike_Variance)
Where variance = square of daily log-returns × 252 (annualized)

**Brazilian market status**: True variance swaps on the Ibovespa are available only from major dealer banks and primarily to large institutional investors and hedge funds (fundos multimercado). Bid-offer spreads are wide compared to developed markets (often 2–3 vol points) due to the relatively thin market. Vega notional (the gain/loss per 1-point move in realized vol) is the typical measure of position size.

**Use cases in Brazil**:
- **Long variance**: Bought by funds expecting volatility to spike (pre-election, pre-Copom). The "vol of vol" in Brazil is high, making variance swaps more expensive to buy relative to other EM markets.
- **Short variance**: Sold by structured product desks and by funds with views that realized vol will remain contained. Income from selling variance historically has been positive in Brazil during politically calm periods (Ibovespa realized vol averages 20–25% annualized vs. implied vol of 22–28%, providing a persistent long-run variance risk premium to sellers).
- **Correlation products**: Some institutions trade correlation swaps or dispersion trades (long variance on index, short variance on constituents), exploiting the difference between implied index variance and weighted average constituent variance.

---

## 25. Deep Dive: Building and Reading the DI Futures Curve {#di-curve-deep-dive}

### 25.1 What the DI Curve Represents

The DI futures curve is the market's collective estimate of the path of the accumulated CDI rate from today through each contract maturity. Each DI futures contract maturing on date T implies that the market expects the accumulated CDI from today to T to equal a specific compounded rate. This makes the DI curve a direct read of monetary policy expectations — no theoretical transformation required.

**Contrast with sovereign bond curve**: In the US, Treasury yields are par yields derived from coupon bond prices. Deriving the zero-coupon rate requires "bootstrapping." The DI futures curve is already a zero-coupon floating rate curve because the contract settles on the accumulated CDI — no coupon stripping needed.

### 25.2 Bootstrapping Zero-Coupon Rates from DI Futures

The DI futures price (PU) is:

**PU = 100,000 / (1 + i_ann)^(n/252)**

Where i_ann is the annual rate implied by the contract and n is the business days to expiry.

**Converting PU to zero-coupon rate**:

i_ann = (100,000 / PU)^(252/n) - 1

**Example**: DI Jan2027 (expiring on January 2, 2027) with PU = 79,345 and n = 500 business days:

i_ann = (100,000 / 79,345)^(252/500) - 1 = (1.26038)^(0.504) - 1 = 1.12743 - 1 = **12.74% per year**

This 12.74% is the zero-coupon rate for the January 2027 maturity — the market's estimate of the average CDI rate over the next 500 business days.

### 25.3 Building the Full DI Curve

The DI curve is built by collecting PU prices from all actively traded DI futures maturities:

| Maturity | Business Days | PU | Zero-Coupon Rate |
|---|---|---|---|
| Jan 2025 | 21 | 99,038 | 11.85% |
| Apr 2025 | 83 | 96,244 | 12.05% |
| Jan 2026 | 271 | 88,612 | 12.35% |
| Jan 2027 | 523 | 79,012 | 12.68% |
| Jan 2029 | 1,027 | 62,845 | 13.10% |
| Jan 2031 | 1,527 | 50,198 | 13.35% |

(Hypothetical illustrative rates)

**Reading the curve**:
- The **short end** (Jan 2025) reflects the current Selic/CDI rate almost exactly
- The **medium term** (Jan 2026 to Jan 2028) reflects monetary policy expectations over the next 1–3 years — this is where Copom rate expectations are most directly priced
- The **long end** (Jan 2029 onwards) incorporates the market's estimate of the long-run neutral real rate plus inflation expectations plus fiscal risk premium

**The "focus rate"**: Market practitioners extract the **implied 1-year forward rate 1 year hence** (1y1y forward) from the DI curve as a cleaner read of where policy is expected to be after any current cycle is complete. The formula:

(1 + rate_2yr)^2 = (1 + rate_1yr) × (1 + forward_1y1y)

### 25.4 Forward DI Rates and Their Uses

Sophisticated fixed income managers use forward rates derived from the DI curve to:

1. **Value swap cash flows**: An IPCA swap paying IPCA + 5.50% receives CDI. The mark-to-market value is computed using DI forward rates to discount each cash flow.

2. **Position on specific segments of the curve**: If a manager believes Copom will cut rates more aggressively in 2026 than the market currently prices, they can position long in DI contracts maturing in 2026 specifically, without taking exposure to 2027+ rate risk.

3. **Detect technical cheapness / richness**: Comparing the DI forward rates to the BCB's published neutral rate estimates and inflation target provides a framework for identifying when the curve has become mispriced.

4. **Relative value across curves**: Comparing Brazil's DI forward rates to equivalent forward rates from Mexico (TIIE curve), Colombia (IBR curve), or Chile (TBC) allows macro managers to identify the most attractive relative value in EM fixed income.

### 25.5 DI Curve During Rate Cycles: Inversion and Normalization

**Inverted DI curves** occur when the market expects the current Selic to be reduced significantly. They signal the market believes the current rate is above neutral. Example: In 2016, with Selic at 14.25%, the DI Jan2019 contract priced at approximately 11.50% — a 275 bps inversion at 2-year tenor, correctly anticipating the eventual Selic cuts to 6.50% in 2018.

**Steep DI curves** occur when the current Selic is below neutral and the market expects tightening. Example: In 2021, with Selic at 2.00%, the DI Jan2024 priced at approximately 9.00% — a 700 bps slope, correctly anticipating the aggressive hiking cycle.

**The DI curve as a signal for duration positioning**: When the curve is deeply inverted and consensus expects cuts, extending duration (buying long-end DI) has historically been highly profitable if the cuts materialize. The challenge is timing the entry before the market consensus shifts.

---

## 26. Agricultural Derivatives: Detailed Specifications and Seasonal Patterns {#agricultural-derivatives}

### 26.1 Soybeans (SFI) — Contract Specifications

**Ticker**: SFI (full) / SFIN (mini, where available)
**Exchange**: B3 (BM&FBovespa segment)
**Underlying**: Soybeans, non-GMO certificate of origin acceptable, delivered FOB at designated Brazilian ports (Paranaguá, Santos, or São Simão)
**Contract size**: 450 bags of 60 kg = 27,000 kg = 27 metric tons
**Quotation**: USD per 60-kg bag (the traditional Brazilian unit of measure for grains)
**Settlement**: Physical or financial; most contracts settle financially by reference to the official B3/ESALQ price bulletin for soybeans at Paranaguá port
**Expiry months**: March, April, May, June, July, August, September, November (reflecting harvest timing and commercial seasons)
**Minimum price tick**: USD 0.01 / bag
**Trading hours**: 09:00 – 18:00 Brasília time

**Seasonal patterns**:
- **January–March**: Peak harvesting of the "safrinha" (second crop, primarily Mato Grosso). Prices often weaken as supply arrives. Basis to CBOT typically widens (Brazilian price trades at larger discount to CBOT due to abundant supply).
- **April–June**: Export surge from Brazilian ports. Ocean freight rates from Brazil to China are a key variable.
- **July–September**: Low inventory period; US crop development (weather risk at CBOT). Brazilian prices can move on US weather without any change in Brazilian fundamentals.
- **October–December**: Brazilian planting season. Pre-planting commercialization by farmers who sell futures before the crop is in the ground.

**Basis calculation example**:
- CBOT November soy futures: USD 12.80 / bushel
- B3 November SFI futures: USD 24.10 / 60-kg bag
- Implied CBOT equivalent: USD 12.80 / bushel × 2.204 bushels / 60 kg = USD 28.21 / 60 kg
- Basis = B3 price - CBOT equivalent = USD 24.10 - USD 28.21 = **-USD 4.11 / 60 kg**
- This negative basis reflects ocean freight (≈USD 3.00–4.00/bag), port costs, and any quality adjustments

### 26.2 Live Cattle (BGI) — Contract Specifications

**Ticker**: BGI
**Underlying**: Boi gordo (fat cattle), "@ arrobas" — the traditional Brazilian unit of cattle weight
**Contract size**: 330 arrobas net (1 arroba = 15 kg; 330 × 15 = 4,950 kg, approximately 1 head of fattened cattle equivalent notional)
**Quotation**: BRL per arroba @ net
**Settlement**: Financial, by reference to B3/CEPEA "Esalq/B3 Boi Gordo" price indicator, collected in 10 states of Brazil
**Expiry months**: Monthly
**Minimum price tick**: BRL 0.01 / @

**Key seasonal pattern**:
- **Dry season (May–September)**: Pasture quality falls in the Center-South. Cattle owners accelerate slaughter (oferta de abate increases), which depresses near-term BGI prices but can create backwardation as future supply appears tighter.
- **Rainy season (October–April)**: Pasture recovery, cattle weight gain. Prices for forward delivery often firm. Seasonal hedging by meatpackers (JBS, Marfrig, Minerva) involves buying BGI futures to lock in cattle costs for future slaughter.

**Export dynamics**: China's beef import quotas and occasional sanitary barriers (foot-and-mouth disease alerts) cause sharp jumps in BGI futures. When China suspended Brazilian beef imports in September 2017 (food safety concerns), BGI fell approximately 5% in two sessions.

**Basis risk for cattle hedgers**: The BGI price reflects an average of 10 Brazilian states. A cattle producer in Mato Grosso do Sul may receive prices materially different from the BGI settlement price depending on local supply/demand conditions, transport costs, and meatpacker slaughter capacity in that region.

### 26.3 Arabica Coffee (ICF) — Contract Specifications

**Ticker**: ICF
**Exchange**: B3
**Underlying**: Arabica coffee, type 6 soft or better, 60-kg bags
**Contract size**: 100 bags (6,000 kg)
**Quotation**: USD per 60-kg bag
**Settlement**: Financial by reference to B3/CECAFÉ price indicator or ICE "C" contract adjusted for Brazil differential
**Expiry months**: March, May, July, September, December (bimonthly plus March, aligned with ICE "C" contract months)

**Brazil-ICE differential**: Brazilian arabica coffee from Minas Gerais (Cerrado, Sul de Minas regions) commands quality premiums or discounts relative to the generic ICE "C" contract standard. The "Brazilian differential" in the physical market ranges from +5 to -20 US cents / pound depending on crop quality (cup quality, bean size, defects).

**Frost risk premium**: Coffee arabica trees in Paraná and southern São Paulo are vulnerable to frost during June–August. A single severe frost event (as occurred in 1994 and 2021) can destroy significant portions of the crop. Coffee futures spikes on frost alerts have historically been among the most violent single-day moves in B3 agricultural derivatives — ICF rose 30%+ in days during the July 2021 frost scare.

**Biennial production cycle**: Brazilian arabica coffee production alternates between "on years" (high production) and "off years" (lower production) due to the biennial bearing cycle of the trees. This creates multi-year predictable patterns in basis and price levels.

### 26.4 Anhydrous Ethanol (ACF) — Contract Specifications

**Ticker**: ACF
**Exchange**: B3
**Underlying**: Anhydrous ethanol (used for blending into gasoline; Brazil mandates 27% ethanol in gasoline mix)
**Contract size**: 30 m³ (30,000 liters)
**Quotation**: BRL per m³
**Settlement**: Financial by reference to CEPEA/ESALQ ethanol price indicator (Anhydrous, Sao Paulo state, producer price)

**Sugar-ethanol flex**: Brazilian sugarcane mills can allocate their cane to either sugar production or ethanol production. The allocation decision is made based on the relative profitability of each:
- When sugar prices (in USD, on ICE 11 or B3 ISU) are high, mills shift to sugar production, reducing ethanol supply and pushing ACF prices higher
- When global sugar prices are depressed, mills shift to ethanol, increasing ethanol supply and suppressing ACF prices

**Gasoline parity**: Ethanol is viable as a consumer fuel when the ethanol price is below approximately 70% of the gasoline price at the pump (consumers' break-even between flex-fuel options). When ethanol is below this threshold, flex-fuel vehicles consume ethanol; when above, they consume gasoline. This demand elasticity creates a soft cap on ACF prices.

**Pre-harvest vs. post-harvest dynamics**: Before the sugarcane harvest (January–March), ethanol stocks are low and prices are typically firm or in backwardation. After harvest begins (April), prices weaken as new supply enters. Traders use this seasonal pattern with a spread trade (long nearby ACF futures, short post-harvest ACF) which typically narrows over the harvest period.

---

## 27. Cross-Currency Swap Mechanics with Detailed Examples {#cross-currency-swaps}

### 27.1 Structure of a BRL/USD Cross-Currency Swap

A cross-currency swap (CCS) between BRL and USD involves the exchange of principal and interest payments in two different currencies over the life of the swap. Unlike a plain interest rate swap (which involves only interest payments), a CCS involves:

1. **Initial principal exchange**: Parties exchange notional amounts in the two currencies at the spot FX rate on trade date
2. **Periodic interest payments**: One party pays BRL-denominated interest (typically CDI or fixed BRL rate); the other pays USD-denominated interest (SOFR or fixed USD rate)
3. **Final principal re-exchange**: At maturity, the initial principal exchange is reversed at the same FX rate agreed on trade date (not at prevailing spot rate — this is the key distinction from a simple FX forward)

**Structure diagram** (BRL-paying / USD-receiving CCS):

```
Company A (BRL borrower)                   Bank (USD provider)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
At Inception:
← USD 100 million ────────────────────────── 
──── BRL 500 million (at 5.00 BRL/USD) ────→

Semi-annually:
← SOFR + 150 bps on USD 100 million ─────── 
──── CDI + 0.80% on BRL 500 million ────────→

At Maturity:
──── USD 100 million ────────────────────────→ 
← BRL 500 million ──────────────────────────
```

The re-exchange of principal at the original rate (BRL 500mm / USD 100mm) means the Company is protected against BRL/USD movements on the principal amount. This is why CCS is used for long-term liability hedging.

### 27.2 Real-World Use Case: Brazilian Infrastructure Company

**Scenario**: Rodovias do Brasil S.A. issues a USD 500 million 10-year bond at SOFR + 3.00% to finance a highway concession. The company's revenues are in BRL (toll revenues). Without hedging, USD debt with BRL revenues creates massive FX mismatch.

**Cross-currency swap executed**:
- Pay USD 500 million initially to bond investors; swap desk arranges CCS where company receives USD 500mm from the bank at inception (offsetting bond proceeds) and pays BRL 2.5 billion (at BRL 5.00 / USD) to the bank
- Periodic payments: Company receives SOFR + 3.00% from the bank (exactly covering bond coupon) and pays CDI + 2.50% in BRL to the bank
- At maturity: Company pays USD 500mm to the bank (to redeem bonds) and receives BRL 2.5 billion from the bank

**Net result**: Company has synthetically issued a BRL CDI + 2.50% bond rather than a USD floating bond. Its BRL revenues from toll collections service the BRL coupon naturally. All USD exposure on the bond is hedged.

**Basis risk in CCS**: The spread paid over CDI (2.50% above) incorporates the "cupom cambial" — the market's pricing of BRL funding vs. USD funding. When Brazilian sovereign risk increases, this spread widens. Companies that locked in CCS during periods of low cupom cambial captured favorable long-term hedging costs.

### 27.3 Pricing a Cross-Currency Swap

The CCS spread over CDI is determined by:

**Cupom cambial** = the implied USD rate of borrowing in BRL via CCS = the interest rate differential minus the forward points.

For a 1-year CCS:
- USD SOFR = 5.00%
- BRL CDI = 11.50%
- Theoretical CCS: Company should pay CDI - 6.50% and receive SOFR (no-arbitrage)
- But practical market: Companies typically pay CDI - 5.00% to CDI - 5.50%, with the difference (50–100 bps) being the CCS basis, which reflects credit risk, liquidity premium, and supply/demand for BRL/USD CCS

**The "cupom sujo" (dirty coupon)**: Because the BRL/USD rate at maturity is locked at inception (not re-marked to market), changes in spot BRL/USD during the life of the swap create mark-to-market gains or losses in addition to the coupon differentials. A Brazilian company that entered into a CCS paying BRL CDI when the spot was BRL 3.50/USD now faces a large MTM gain (the USD notional is worth much more BRL at current BRL 5.20/USD rates) — this is the "translation gain" but creates asymmetric accounting complexity.

---

## 28. Institutional ALM: How Pension Funds and Insurers Use Derivatives {#institutional-alm}

### 28.1 The ALM Problem for Brazilian Pension Funds

Brazilian closed pension funds (EFPCs — Entidades Fechadas de Previdência Complementar) manage liabilities that are:
- Long-duration (pension payments extend 30–50 years into the future)
- Inflation-indexed (most pension benefits are adjusted by INPC or IPCA annually)
- Actuarially estimated based on mortality tables, contribution rates, and actuarial interest rate assumptions (typically 4–6% real per year)

**The fundamental mismatch**: A pension fund with liabilities indexed to IPCA and spanning 30 years needs assets that produce IPCA + 4–5% over a very long horizon. Brazilian capital markets offer NTN-B bonds (IPCA + fixed spread) as the natural asset for this purpose, but:
- Long-dated NTN-B liquidity is limited (market for NTN-B 2045 or 2055 is thin)
- Duration of available NTN-B bonds may not match liability duration
- Liquidity needs require holding shorter-dated assets that then require swapping

**Derivatives as the solution**:

**IPCA Swap (CDI × IPCA swap)**:
- Pension fund holds CDI-linked CDBs or LFTs (liquid, short-term)
- Enters into OTC swap: Pays CDI to the bank, Receives IPCA + 5.00% from the bank
- Net result: Pension fund has converted its floating CDI exposure into a long real rate position (IPCA + 5.00%), which matches its liability structure

**Duration extension via DI futures**:
- Pension fund holds a ladder of NTN-B bonds with maturities out to 15 years
- Uses DI futures (sell Jan2040 DI futures) to extend effective duration to match 30-year liabilities
- The futures position adds negative convexity, which must be monitored

**Ibovespa futures for equity beta management**:
- Under CMN Resolution 4,994, pension funds may allocate up to a specified percentage to equities
- Rather than maintaining exact equity allocations through frequent rebalancing (costly in transaction costs), they use Ibovespa futures to manage tactical equity beta — increasing futures during market dislocations (cheaply buying equity exposure) and reducing when equity risk premium is thin

### 28.2 Insurance Company Liability Matching

Brazilian insurance companies (seguradoras) regulated by SUSEP face similar ALM challenges but with specific product structures:

**PGBL/VGBL (annuity-type pension products)**: Insurers offering PGBL products have liabilities that are often floating (CDI-linked) in the accumulation phase. Upon annuitization, they become INPC-linked. Derivatives bridge:
- Pre-annuitization: Match CDI-linked liabilities with CDI assets (no derivatives needed)
- At annuitization: Convert CDI assets to INPC-linked via CDI × INPC swap

**Life insurance reserves**: Reserves for term life insurance are discounted at regulated interest rates (Susep sets discount rates for reserves). When market interest rates fall below reserve discount rates, insurers face solvency pressure. Swaptions (options to enter into interest rate swaps) can hedge this risk — an insurer buying a receiver swaption gains the right to receive fixed and pay floating, which gains value when rates fall.

**Property/casualty (P&C) insurance**: Brazilian P&C companies face currency risk when reinsurance treaties are denominated in USD. They use dollar futures or NDF contracts to hedge USD reinsurance premiums and claims payments.

### 28.3 Corporate Treasury ALM: Brazilian Infrastructure Concessionaire

An infrastructure concessionaire (e.g., toll road, airport, port terminal) typically has:
- **Revenues**: BRL, indexed to IPCA (tariffs adjusted annually by inflation)
- **Debt**: Mix of BRL fixed, BRL CDI-linked, and potentially USD-denominated (for international bond issuances)
- **Capital expenditure**: Mix of BRL and USD (imported equipment)

**Derivative strategy**:
1. **Convert USD debt to BRL via CCS**: Described in Section 27.2 above
2. **Convert CDI-linked debt to fixed via interest rate swap**: Pay fixed BRL, receive CDI — converts variable interest expense to predictable fixed cost, matching the predictable nature of IPCA-linked revenues
3. **IPCA floor**: Buy an IPCA floor option (protection against deflation, which would reduce tariff revenues below planned levels)

The combined hedge results in: IPCA-indexed revenue stream → fixed cost structure → predictable cash flows for debt service.

---

## 29. Regulatory Deep Dive: CMN, CVM, BCB, and DREX Implications {#regulatory-deep-dive}

### 29.1 Regulatory Architecture

The Brazilian financial regulatory system is a tripartite structure:

**CMN (Conselho Monetário Nacional)** — apex policy body:
- Composed of the Finance Minister, Planning Minister, and BCB President
- Issues Resoluções CMN that govern all financial system rules
- Does not supervise directly — issues policy frameworks implemented by BCB and CVM
- Key CMN resolutions for derivatives: CMN 4,994 (pension fund investment rules), CMN 4,373 (foreign investor access, now updated), various anti-money laundering frameworks

**BCB (Banco Central do Brasil)** — financial stability and monetary authority:
- Supervises banks (bancos múltiplos, caixas econômicas, cooperativas de crédito)
- Issues Circulares BCB and BCB Resoluções governing specific operational rules
- Runs the SPB (Sistema de Pagamentos Brasileiro) settlement infrastructure
- Oversight of FX market: All BRL/foreign currency transactions must be registered with BCB. B3 is the designated trade repository.
- Basel III capital requirements: BCB's regulatory capital rules (Circular 3,644 and related) govern how banks must capitalize their derivatives books. Market risk (VaR-based) and CVA capital requirements apply.

**CVM (Comissão de Valores Mobiliários)** — securities and capital markets:
- Supervises investment funds, broker-dealers, investment banks, listed companies
- CVM Resolution 175 (2022) replaced the previous Instrução 555 regime, modernizing the Brazilian investment fund regulatory framework
- Key fund derivatives rules: Funds must disclose derivative exposure (long, short, leveraged), risk limits, and stress test results in quarterly disclosures (IAN/DFP reports for public funds)
- CVM Instruction 361 governs tender offers, which often involve derivatives (price stabilization, greenshoe options)

**B3 as SRO (Self-Regulatory Organization)**:
- B3 BSM (B3 Supervisão de Mercados) conducts real-time market surveillance
- Can temporarily restrict position sizes, request explanations from members, and refer cases to CVM/BCB
- B3 Circular specifies margin requirements, daily price limits (circuit breakers), and position limit frameworks

### 29.2 Position Limits and Reporting Requirements

**Position Limits on Commodity Futures**:

| Contract | Single Client Limit | Direction |
|---|---|---|
| BGI (Live Cattle) | 3,000 contracts (net per direction) | Long or short |
| ICF (Arabica Coffee) | 2,000 contracts | Long or short |
| ACF (Ethanol) | 500 contracts | Long or short |
| SFI (Soybeans) | 5,000 contracts | Long or short |

Limits are higher during "spot month" (front-month before delivery) and may be reduced by B3 BSM during periods of thin liquidity or suspicious activity.

**Reporting thresholds**:
- Positions above 300 DI contracts of any single maturity: Must be reported to B3 with client identification
- BRL/USD futures positions above USD 100 million (equivalent): Reportable to BCB under systemic risk monitoring framework
- Non-residents: Must report aggregate derivative positions to BCB via their custodian banks monthly

**EMIR-equivalent trade repository reporting**:
All OTC derivatives between regulated entities must be reported to B3's trade repository within T+1. This captures: trade date, counterparties, notional, maturity, trade type, margin posted. BCB and CVM access aggregate data for systemic risk monitoring.

### 29.3 DREX: Brazil's Central Bank Digital Currency and Derivatives Implications

The BCB's DREX (Digital Real — Depósito Digital) project — Brazil's wholesale CBDC initiative — has significant potential implications for derivatives settlement and margining:

**What DREX is**: A wholesale digital currency issued by the BCB and held by financial institutions (not directly by the public). Retail access would be through "DREX tokenizado" issued by commercial banks — a tokenized form of bank deposits backed 1:1 by the BCB's DREX.

**Phase 1 Pilots (2023–2024)**: The BCB ran a pilot involving Brazilian banks and technology partners (Itaú, Bradesco, BTG, Santander, XP) exploring use cases: government bond tokenization, DvP (delivery vs. payment) settlement, and repo transactions on distributed ledger technology (DLT).

**Derivatives implications**:

1. **Atomic settlement**: DREX enables "atomic" (simultaneous) exchange of derivatives settlement amounts and collateral on DLT. Today, DI futures settlement occurs T+0 on the SPB, but margining and daily P&L settlement involve multiple separate steps. Atomic settlement could reduce settlement risk and intraday liquidity needs.

2. **Smart contract-based derivatives**: Derivatives terms encoded in smart contracts would auto-execute based on observable price feeds (oracles). An interest rate swap encoded in a DREX-compatible smart contract could automatically calculate and transfer the net payment based on BCB-published CDI rates — eliminating counterparty settlement risk.

3. **Collateral efficiency**: DREX-based government bonds (tokenized NTN-B, NTN-F) could be posted as margin for derivatives positions in near-real-time, reducing the need for cash margin buffers. Today, LFTs must be physically transferred through the SELIC custody system for margin purposes — a process with T+0 but operationally cumbersome.

4. **Foreign investor access**: DREX could simplify foreign investor access to BRL derivatives by enabling programmable compliance (KYC/AML via digital identity) and reducing the administrative burden of the current CMN 4,852 framework.

**Timeline and caution**: As of early 2025, DREX remains in the pilot phase. Full commercial implementation is targeted for 2026–2027. Advisors should monitor BCB DREX communications for regulatory developments that may affect derivatives settlement infrastructure.

---

## 30. Glossary of Brazilian Derivatives Terms {#glossary}

**Ajuste Diário (Daily Adjustment)**: The daily mark-to-market cash settlement of futures positions. Gains are credited and losses debited to the margin account each evening. This is the fundamental mechanism by which futures positions avoid accumulating credit risk.

**Arbitragem (Arbitrage)**: Simultaneous purchase and sale of equivalent positions to profit from price discrepancies without directional risk. Example: buying BOVA11 (Ibovespa ETF) and shorting Ibovespa futures when futures trade rich to fair value.

**Alavancagem (Leverage)**: The use of derivatives to control an exposure larger than the capital invested. Brazilian investment funds must disclose if gross derivative exposure exceeds fund NAV.

**Arroba (@)**: The traditional Brazilian unit of cattle weight, equal to 15 kg. Live cattle (BGI) futures are quoted in BRL per arroba.

**Basis**: The difference between two prices that should theoretically converge. In agricultural markets: spot price minus futures price. In FX: offshore NDF price minus onshore futures price.

**BGI**: B3 ticker for live cattle (boi gordo) futures contracts.

**BM&FBovespa**: The predecessor exchange formed from the merger of Bolsa de Mercadorias e Futuros (BM&F) and Bolsa de Valores de São Paulo (Bovespa) in 2008. Now operates as B3.

**Câmara B3**: B3's central counterparty clearing house (CCP). Interposes itself between buyers and sellers in all exchange-traded derivatives, eliminating bilateral counterparty risk.

**Casado (Spread entre Dólar Futuro e Cupom Cambial)**: The "married" trade combining a dollar futures position with a CDI investment. The casado rate is the implied USD cost of funds in Brazil, equal to the dollar futures rate minus the CDI.

**CDI (Certificado de Depósito Interbancário)**: The overnight interbank lending rate in Brazil. Tracks the Selic almost exactly (typically 1–2 bps below). The reference rate for most floating-rate instruments and the floating leg of most interest rate swaps.

**CETIP**: The former OTC clearing and trade repository for fixed income and derivatives, merged into B3 in 2017. The CETIP segment now processes OTC swap registration and debenture custody.

**Contraparte Central Garantidora (CCP)**: Central Counterparty Clearing House. The entity (in Brazil, the Câmara B3) that becomes the buyer to every seller and seller to every buyer, guaranteeing contract performance.

**Cupom Cambial**: The implied USD interest rate in the Brazilian onshore FX market, derived from the difference between the DI rate and the forward USD premium. Formula: (1 + CDI) / (1 + cupom) = forward / spot. Positive cupom cambial means onshore USD borrowing is cheaper than the DI rate.

**Cupom de IPCA (Real Rate Curve)**: The real interest rate implied by NTN-B bond prices. The NTN-B yield minus IPCA inflation gives the real yield (cupom de IPCA), analogous to TIPS yields in the US.

**Delta (Δ)**: The rate of change of an option's price relative to changes in the underlying price. Delta = 1 means the option price moves BRL 1 for every BRL 1 move in the underlying.

**DI (Depósito Interbancário)**: The accumulated interbank deposit rate — the underlying of DI futures. The DI rate accumulates daily based on the CDI, which is set by the Brazilian interbank market (effectively tracking the Selic).

**DI1 (DI Futures — Full Contract)**: The full-size DI futures contract on B3. Notional of BRL 100,000. The primary instrument for hedging and speculating on Brazilian interest rates.

**DOL (Dólar Futuro — Full Contract)**: Full-size dollar futures contract on B3. USD 50,000 per contract. The primary institutional FX hedging instrument.

**DV01 (Dollar Value of 1 Basis Point)**: The change in portfolio or instrument value for a 1 basis point (0.01%) change in interest rates. Used to measure interest rate sensitivity and calculate hedge ratios.

**EFPC (Entidade Fechada de Previdência Complementar)**: Closed pension fund. The institutional investors managing pension assets in Brazil. Subject to CMN Resolution 4,994 investment guidelines.

**Exercício (Exercise)**: The act of exercising an option — a call option buyer demands delivery of the underlying at the strike price; a put option buyer demands sale of the underlying at the strike price.

**Gamma (Γ)**: The rate of change of delta relative to changes in the underlying price. High gamma means delta changes rapidly — options near expiry and ATM options have the highest gamma.

**Greeks**: Measures of option sensitivity: Delta (price), Gamma (delta change), Vega (volatility), Theta (time decay), Rho (interest rate). Essential tools for option book management.

**IND (Índice Futuro — Full Contract)**: Full-size Ibovespa futures contract. BRL 1.00 per index point. At Ibovespa 125,000, each contract = BRL 125,000 notional.

**IOF (Imposto sobre Operações Financeiras)**: Financial transactions tax. Applies to certain derivative transactions; rate is 0% for most exchange-traded derivatives between financial institutions. May apply at higher rates for specific structures or in response to capital flow management.

**IPCA (Índice Nacional de Preços ao Consumidor Amplo)**: Brazil's official consumer price index, measured by IBGE monthly. The target variable for BCB's inflation targeting regime. Components include food, housing, transportation, healthcare.

**ISDA**: International Swaps and Derivatives Association. ISDA Master Agreements govern most OTC derivative transactions globally, including those executed between Brazilian and foreign counterparties.

**Lançamento Coberto (Covered Call Writing)**: Selling call options against a long stock position. The most common retail derivatives strategy in Brazil.

**Liquidação Financeira (Financial Settlement)**: Cash settlement of a derivatives contract at expiry, based on the reference price. Most Brazilian derivatives (DI, dollar futures, Ibovespa) settle financially.

**Margem de Garantia (Margin Deposit)**: Collateral deposited with the CCP to guarantee performance of futures and options obligations. Can be posted in cash, LFTs, or other eligible securities.

**NDF (Non-Deliverable Forward)**: A forward FX contract settled financially (no physical currency delivery) at maturity based on the official BRL/USD PTAX rate. Used in the offshore market by foreign investors who cannot access the Brazilian onshore FX market directly.

**NTN-B (Nota do Tesouro Nacional Série B)**: Brazilian government inflation-linked bond, paying IPCA + fixed coupon semiannually. The benchmark inflation-linked government security.

**NTN-F (Nota do Tesouro Nacional Série F)**: Fixed-rate government bond, paying a fixed coupon semiannually and par at maturity. Pre-fixed government benchmark.

**Open Interest**: Total number of outstanding (not yet settled or closed) derivative contracts for a given instrument and maturity. High open interest indicates liquid markets; rapid open interest build-up may signal speculative positioning.

**Opção (Option)**: A contract giving the buyer the right (not obligation) to buy (call) or sell (put) an underlying asset at a specified price (strike) on or before a specified date (expiry). The seller (writer) receives a premium and is obligated to fulfill if exercised.

**Opção Americana (American Option)**: An option exercisable at any time up to expiry. Most Brazilian equity options (individual stock options) are American-style.

**Opção Europeia (European Option)**: An option exercisable only at expiry. Ibovespa options and most index options are European-style.

**PTAX**: The official BRL/USD exchange rate published daily by the BCB, calculated as the weighted average of USD spot transactions in the Brazilian FX market during the trading day. The reference for settlement of FX derivatives.

**PU (Preço Unitário)**: Unit price of a DI futures contract. PU = 100,000 / (1 + rate)^(n/252). The price at which DI contracts trade on B3.

**Roll (Rolagem)**: Closing an expiring futures position and opening a new position in the next available maturity to maintain continuous exposure.

**Selic**: The Brazilian overnight policy rate, set by the Copom. Also the name of the government securities custody system (Sistema Especial de Liquidação e de Custódia).

**Spread (Calendar Spread)**: A simultaneous long position in one futures maturity and short position in another maturity of the same underlying. Traded to profit from changes in the curve shape rather than the outright level.

**SUSEP (Superintendência de Seguros Privados)**: Brazil's insurance regulatory authority. Oversees insurance companies, reinsurers, open pension funds (EAPCs), and capitalization bonds.

**Swap Cambial (FX Swap)**: A BCB instrument auctioned to provide USD liquidity to the market. BCB pays BRL CDI and receives USD + FX change from the market (bank counterparties). Effectively a USD repo for the market. Distinguished from a commercial cross-currency swap.

**Termo (Forward on Equities)**: A forward contract on individual stocks traded on B3. The buyer agrees to purchase a specified number of shares at a fixed price on a future date. The seller finances the position (typically paying CDI) until delivery.

**Theta (Θ)**: The rate of decline in an option's value due to the passage of time ("time decay"). All long option positions lose value every day due to theta, all else equal.

**Vega (V)**: The rate of change of an option's price relative to changes in implied volatility. Long options are long vega (benefit from rising implied vol); short options are short vega.

**Volatilidade Implícita (Implied Volatility)**: The market's expectation of future price volatility, extracted from option prices using an options pricing model (typically Black-Scholes). Brazilian implied volatility is historically elevated compared to developed markets.

**WDO (Mini Dólar)**: Mini dollar futures contract on B3. USD 10,000 per contract (one-fifth of the full DOL contract). The most actively traded contract by retail day traders in Brazil.

**WIN (Mini Ibovespa)**: Mini Ibovespa futures contract on B3. BRL 0.20 per index point (one-fifth of the full IND contract). Accessible to retail investors with relatively small capital.

---

## 31. Appendix: Contract Specifications for Major B3 Derivatives Contracts {#appendix-contracts}

### 31.1 Complete Contract Specification Table

| Contract | Code | Underlying | Contract Size | Quote Unit | Settlement | Expiry Cycle | Margins (approx.) | Circuit Breaker |
|---|---|---|---|---|---|---|---|---|
| DI Futures (Full) | DI1 | Accumulated CDI | BRL 100,000 notional | PU (100,000 ÷ (1+i)^(n/252)) | Financial (PU = 100,000) | Monthly, 1st biz day of month | BRL 2,500–5,000/contract depending on maturity | ±3% daily |
| DI Futures (Mini) | — | Accumulated CDI | BRL 50,000 notional | PU | Financial | Monthly | BRL 1,250–2,500/contract | ±3% daily |
| Dollar Futures (Full) | DOL | BRL/USD (PTAX) | USD 50,000 | BRL per USD (4 decimals) | Financial (PTAX next day) | Monthly, 1st biz day of month | BRL 3,000–6,000/contract | ±3% daily |
| Dollar Futures (Mini) | WDO | BRL/USD (PTAX) | USD 10,000 | BRL per USD (4 decimals) | Financial (PTAX) | Monthly, 1st biz day | BRL 600–1,200/contract | ±3% daily |
| Ibovespa Futures (Full) | IND | Ibovespa Index | BRL 1.00 × Index pts | Index points | Financial (avg of last hour) | Bimonthly (even months), 3rd Mon | BRL 10,000–15,000/contract | ±10% (15-min halt); ±15% (session halt) |
| Ibovespa Futures (Mini) | WIN | Ibovespa Index | BRL 0.20 × Index pts | Index points | Financial | Bimonthly | BRL 2,000–3,000/contract | Same as IND |
| Ibovespa Options | OI | IND contract | BRL 1.00 × Index pts | Premium in index pts | Financial (on exercise) | Monthly + bimonthly | Premium + potential naked margin | Underlying-based |
| PETR4 Options | PETR4C/P | PETR4 shares | 100 shares | BRL per share | Physical (delivery of shares) | Monthly (3rd Friday) | 20% of underlying for naked puts | Underlying-based |
| VALE3 Options | VALE3C/P | VALE3 shares | 100 shares | BRL per share | Physical | Monthly (3rd Friday) | 20% of underlying for naked puts | Underlying-based |
| Live Cattle (BGI) | BGI | Boi gordo (ESALQ/B3 price) | 330 @ net | BRL per @ | Financial (ESALQ indicator) | Monthly | BRL 1,500–3,000/contract | ±5% daily |
| Arabica Coffee | ICF | Arabica coffee 60-kg bags | 100 bags | USD per 60-kg bag | Financial (CECAFÉ indicator) | Bimonthly (Mar, May, Jul, Sep, Dec) | BRL 1,200–2,500/contract | ±5% daily |
| Anhydrous Ethanol | ACF | Anhydrous ethanol | 30 m³ | BRL per m³ | Financial (CEPEA indicator) | Monthly | BRL 800–1,500/contract | ±5% daily |
| Soybeans | SFI | Soybeans (ESALQ/B3 price) | 450 bags 60 kg | USD per 60-kg bag | Financial (port indicator) | Mar, Apr, May, Jun, Jul, Aug, Sep, Nov | BRL 1,000–2,000/contract | ±5% daily |
| Corn | CCM | Corn (ESALQ price) | 450 bags 60 kg | BRL per 60-kg bag | Financial | Mar, May, Jul, Aug, Sep | BRL 800–1,500/contract | ±5% daily |
| Sugar Crystal | ISU | Crystal sugar | 270 bags 50 kg | BRL per 50-kg bag | Financial | Mar, May, Jul, Oct, Dec | BRL 600–1,200/contract | ±5% daily |
| OTC Interest Rate Swap | — | CDI / Fixed / IPCA | Custom notional | Rate % p.a. | Financial at maturity / periodic | Custom, registered at B3 | Bilateral margin per ISDA or B3 | N/A |
| NDF (Dollar, offshore) | — | BRL/USD (PTAX) | Custom notional | BRL per USD | Financial (PTAX) | Custom maturity | Bilateral credit/ISDA CSA | N/A |
| Cross-Currency Swap | — | BRL CDI / USD SOFR | Custom notional | Rate % | Financial periodic + principal | Custom | Bilateral margin or CCP at B3 | N/A |

### 31.2 Key Margin Rates and Collateral Eligibility

**Eligible margin collateral at B3**:

| Collateral Type | Haircut | Notes |
|---|---|---|
| Cash (BRL) | 0% | Full face value accepted |
| LFT (floating-rate government bond) | 0% | Considered near-cash |
| NTN-B (inflation-linked government bond) | 2–5% depending on maturity | High quality; duration risk haircut |
| NTN-F (fixed-rate government bond) | 3–8% depending on maturity | Duration risk haircut |
| CDB from eligible banks | 3–10% depending on bank credit rating | Issuer credit risk haircut |
| Investment-grade corporate bonds | 10–20% | Less commonly used |
| BOVA11 ETF units | 15% | Subject to equity vol haircut |

**Dynamic margin**: B3 updates margin requirements daily (sometimes intraday during volatile sessions). Margin models use portfolio-level stress testing (CORE — Core-to-Core Risk Engine) rather than simple contract-by-contract VaR, which allows netting of correlated positions across asset classes. A portfolio with long Ibovespa futures and short dollar futures (natural BRL-bullish correlated positions) may receive a margin benefit versus holding each position in isolation.

### 31.3 Trading Hours Summary

| Contract Group | Regular Hours (Brasília) | Extended Hours (Brasília) |
|---|---|---|
| DI Futures | 09:00 – 18:00 | 18:00 – 18:15 |
| Dollar Futures (DOL/WDO) | 09:00 – 18:00 | 18:00 – 20:00 (US market close) |
| Ibovespa Futures (IND/WIN) | 09:00 – 17:55 | 18:00 – 18:15 |
| Equity Options (PETR4, VALE3, etc.) | 10:00 – 17:55 | No extended hours |
| Agricultural Futures (BGI, ICF, SFI) | 09:00 – 15:30 (or specific schedules) | Limited after-hours for some |
| Ibovespa Options | 10:00 – 17:55 | No extended hours |

---

*This advanced reference section was prepared by the Decade Investment Research team as an extension of the core derivatives guide. It covers detailed mechanics, historical context, and practical tools for sophisticated users of Brazilian derivatives markets. All contract specifications are approximate and subject to change by B3; verify current specifications at b3.com.br before transacting. Examples are illustrative and do not constitute investment advice.*

---

**Decade Investment Research**
*Conviction | Clarity | Consistency*
