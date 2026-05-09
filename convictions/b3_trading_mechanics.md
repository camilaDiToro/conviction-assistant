# B3 Exchange Trading Mechanics: A Technical Reference for Investment Professionals

**Decade Investment Research | Conviction Document**
*For distribution to advisors and qualified investors only*

---

## Executive Summary

A thorough understanding of B3's trading infrastructure is not merely academic — it directly affects execution quality, cost management, and risk control for every transaction placed on behalf of Decade clients. This document provides a comprehensive technical reference covering B3's market structure, order types, settlement mechanics, clearing and custody architecture, short selling and securities lending, ETF mechanics, circuit breakers, IPO mechanics, fees, and market data infrastructure. Advisors working across equities, ETFs, and fixed income segments of B3 will find this document a practical operational companion.

---

## Trading Sessions

B3 operates a structured trading day segmented into distinct sessions, each with different operational characteristics and purposes.

### Pre-Market Session (Pré-Abertura / Call Phase)

The trading day begins with a **pre-opening call auction** (leilão de pré-abertura), typically running from **09:45 to 10:00 Brasília time**. During this period:
- Orders can be entered, modified, or cancelled.
- No trades execute — the matching engine accumulates orders without crossing them.
- At the close of the call phase, the system runs a theoretical opening price algorithm that maximizes the volume of shares traded at the single clearing price.
- The theoretical opening price (Preço Teórico de Abertura, PTA) is displayed in real time as orders accumulate.

The pre-opening call is particularly important for stocks with overnight news (earnings releases, material facts) as it allows price discovery to occur in a controlled environment before continuous trading begins.

### Continuous Trading Session

Continuous trading runs from **10:00 to 17:00 Brasília time** for equities, with minor variations for futures (which extend to 17:30 or later). During this session, orders are matched in real time on a price-time priority basis. B3 uses an electronic order book (MEGA Bolsa / PUMA Trading System) for all equity and equity derivative instruments.

Key characteristics:
- **Price-time priority**: At identical prices, the order placed earliest has priority of execution.
- **Continuous matching**: There is no periodic batch clearing; orders match as soon as a crossing condition exists.
- **Market surveillance**: B3's surveillance system (SMAC — Sistema de Monitoramento Automatizado de Condições) runs continuously, flagging anomalous price movements and potentially triggering trading halts.

### After-Market Session (After-Hours)

B3 operates an **after-market session from 17:30 to 18:00** for certain eligible securities. Restrictions apply:
- Only market and limit orders are accepted (no stop orders).
- Prices are capped at ±2% from the closing price of the regular session.
- Volumes are typically very thin; liquidity is concentrated in the most active large-cap names.
- Settlement follows the same T+2 cycle as regular session trades.

The after-market session is primarily used for retail order routing following the close of regular trading. Institutional order flow is negligible during this session; advisors should caution clients about execution quality in after-hours trading.

---

## Order Types

B3's PUMA Trading System supports a comprehensive range of order types. Understanding the mechanics of each is essential for optimal execution.

### Market Order (Ordem a Mercado)

A market order instructs the system to execute at the best available price immediately. The order will walk the book — consuming all available liquidity at successively worse prices — until fully filled or until the book is exhausted. Market orders are subject to **price protection bands** (faixas de proteção) that prevent execution beyond a specified threshold from the last traded price; if the band is breached, the order is held pending confirmation or cancellation.

**Use case**: Situations where speed of execution is paramount and price precision is secondary. Inadvisable for illiquid stocks where the market impact can be severe.

### Limit Order (Ordem Limitada)

A limit order specifies the maximum price (for buys) or minimum price (for sells) at which the investor is willing to transact. The order rests in the book until filled, partially filled, or cancelled. Limit orders:
- Provide price certainty but not execution certainty.
- Can be designated as **Day orders** (expire at session close), **Good Till Cancel (GTC)** orders, or **Fill or Kill (FOK)** / **Immediate or Cancel (IOC)** orders.
- Are the dominant order type in institutional equity execution.

### Stop Orders

Stop orders activate when the security reaches a specified trigger price, converting into either a market order (stop-market) or a limit order (stop-limit) upon activation.

- **Stop-loss**: Trigger set below current price; activates on downward price movement. Used for portfolio protection.
- **Stop-gain**: Trigger set above current price; activates on upward movement. Used for take-profit automation.
- **Stop-limit**: Provides the security of a limit order post-activation, preventing the order from executing beyond a specified price band — at the cost of potential non-execution if the market moves through the limit level.

### Iceberg Orders

An iceberg order (ordem iceberg) is a large order whose full size is not displayed in the public order book. Only a specified "peak" quantity is visible at any time; as the visible portion is consumed by incoming orders, the next portion automatically refreshes. This mechanism:
- Reduces market impact for large institutional orders.
- Prevents other market participants from frontrunning a known large order.
- Is widely used by institutional desks managing block executions.

B3's PUMA system requires the peak quantity to be at least 5% of the total iceberg order size, with a minimum absolute peak of 100 shares (for round-lot securities).

---

## Lot Sizes: Round Lot vs. Fractional

### Round Lot (Lote Padrão)

The standard trading unit on B3. For most equity securities, the round lot is 100 shares. Round-lot trading takes place in the primary (BOVESPA) market segment with full order book depth and standard market-making obligations.

### Fractional Market (Mercado Fracionário)

B3 operates a separate **fractional market** for trading quantities below one round lot (i.e., 1 to 99 shares). Fractional shares trade under a distinct ticker suffix ("F" appended to the standard ticker: PETR4F, VALE3F, etc.). Key characteristics:
- Liquidity is significantly thinner than the round-lot market; bid-ask spreads are typically wider.
- Fractional orders cannot be placed as iceberg orders.
- Execution costs per share are proportionally higher due to minimum fee structures.
- Settlement follows the same T+2 cycle.

For retail investors making small investments (BRL 500–2,000) in high-priced stocks, the fractional market enables participation without requiring the full round-lot commitment. Advisors should monitor fractional execution costs, which can represent a significant percentage drag on small transaction sizes.

---

## Settlement: T+2 for Equities

**Equity trades on B3 settle on a T+2 basis** — two business days after the trade date. On settlement date, the seller delivers shares through the CBLC (Companhia Brasileira de Liquidação e Custódia) system, and the buyer delivers funds, with B3 acting as the central counterparty (see Clearing section).

Key settlement mechanics:
- **Delivery vs. Payment (DVP)**: Settlement occurs on a simultaneous delivery versus payment basis. Shares and funds move simultaneously, eliminating principal risk.
- **Settlement finality**: Once settlement occurs, it is final and irrevocable. B3 guarantees settlement even if one counterparty defaults (using the CCP guarantee structure).
- **Ex-dividend date**: The ex-dividend date for equities is typically D+1 after the record date announcement. Investors purchasing on the ex-date do not receive the declared dividend.
- **Failed settlements**: If a seller cannot deliver shares by T+2, B3 initiates a buy-in process, purchasing shares in the market at the defaulting seller's cost. This is uncommon in normal market conditions but can occur during securities lending recall events.

Options and futures contracts have distinct settlement cycles. Equity options typically settle D+1 (exercised options) or continue to trade. Index futures roll quarterly. Fixed income securities (debentures, government bonds) may have D+0 or D+1 settlement in some segments.

---

## Clearing: B3 as Central Counterparty (CCP)

B3 performs the clearing function for all trades executed on its platforms, acting as the **central counterparty (CCP)** through its integrated clearing infrastructure. When two investors execute a trade, B3 legally interposes itself — becoming the buyer to every seller and the seller to every buyer — thereby eliminating bilateral counterparty risk.

The CCP function is supported by a multi-layer risk management structure:
1. **Margin requirements**: Participants must post margin (collateral) commensurate with their open positions and settlement obligations.
2. **Default fund (fundo de participante)**: All clearing members contribute to a mutualized default fund (equivalent to the "default fund" concept at other CCPs) that can absorb losses from a clearing member default.
3. **B3's own capital**: As a final backstop, B3 commits its own capital to the default waterfall.
4. **Insurance arrangements**: B3 maintains insurance coverage for catastrophic loss scenarios.

**CBLC (Companhia Brasileira de Liquidação e Custódia)** is B3's integrated CSD (Central Securities Depository) and settlement infrastructure. Shares purchased on B3 are held in book-entry form at the CBLC, with positions maintained in investor accounts (contas de custódia) linked to their CPF (for individuals) or CNPJ (for entities). The CBLC has no physical share certificates — all holdings are dematerialized entries in the CBLC system.

---

## Margin Requirements

B3 uses a sophisticated risk-based margining system — the **CORE (Closeout Risk Evaluation)** methodology — to calculate margin requirements for derivatives and leveraged positions. Key features:

- **Portfolio margining**: CORE margines at the portfolio level, netting offsetting positions (e.g., long call and short stock) and reducing aggregate margin requirements compared to position-by-position margining.
- **Stress scenarios**: CORE calibrates margin to cover losses in a defined set of historical and hypothetical stress scenarios (including BRL devaluation events, commodity shocks, and equity market crashes).
- **Daily mark-to-market**: Variation margin (ajuste diário) is calculated daily. Positions that have lost value result in margin calls settled in cash the following morning.
- **Eligible collateral**: B3 accepts a range of collateral types, including government bonds (NTN-B, LFT), bank guarantees (cartas de fiança bancária), and gold. Haircuts apply to non-cash collateral based on market risk characteristics.

For equity positions (non-leveraged), no margin is required — the investor simply must have funds available for settlement. Margin requirements kick in for options, futures, and leveraged ETF products.

---

## Short Selling Mechanics

Short selling — selling borrowed shares with the intention of buying them back at a lower price — is permitted on B3 for eligible securities. The mechanics involve the **BTC (Banco de Títulos CBLC)** securities lending system (see next section) and specific settlement procedures.

**Short selling process**:
1. The investor instructs their broker to sell short a specified quantity.
2. The broker locates the securities through the BTC or its own inventory.
3. The short sale executes on B3 with normal trade mechanics.
4. Settlement on T+2 requires the delivery of shares — which the short seller does not own. The borrowed shares (from BTC) are delivered at settlement.
5. The short position remains open until the investor buys back the shares (cover) and returns them to the lender through BTC.

**Short sale restrictions**: B3 and the CVM enforce restrictions on "naked" short selling (selling shares without a locate). All short sales must be backed by an active securities lending agreement through BTC. During periods of extreme market stress, additional restrictions on short selling may be imposed by CVM decree.

---

## Securities Lending: The BTC (Banco de Títulos CBLC)

The **BTC (Banco de Títulos CBLC)** is B3's integrated securities lending platform. It serves as the marketplace where investors who own shares (lenders) make them available to borrowers (typically short sellers, ETF market makers, or arbitrageurs needing shares for settlement).

**BTC mechanics**:
- **Lenders** register their shares as available for lending at a specified minimum rate (taxa de aluguel, expressed as an annualized percentage of the security's value). Institutional investors and funds are the dominant lenders.
- **Borrowers** access the BTC to locate shares for borrowing, accepting the prevailing lending rate for the desired duration.
- **Rates**: BTC lending rates are determined by supply and demand for each specific security. Hard-to-borrow stocks (alta demanda) can trade at lending rates of 20–50%+ annualized; easy-to-borrow large-caps may trade at 0.5–2% annually.
- **Dividends**: The borrower is responsible for paying to the lender any dividends (or JCP) distributed on borrowed shares during the loan period, as the lender retains economic rights.
- **Collateral**: Borrowers post collateral (typically 102–105% of the market value of borrowed shares) with B3.
- **Term**: Loans can be structured as demand (callable by either party with D+1 notice) or term (fixed duration).

For income-focused clients with long-term equity holdings, participation in the BTC as a lender represents a practical source of additional income — often 0.5–3% annualized on blue-chip holdings — with minimal operational burden. Decade's custody platform facilitates BTC participation for eligible client accounts.

---

## ETF Creation and Redemption Mechanics

ETFs (Exchange Traded Funds) on B3 trade like stocks in the secondary market, but their supply is managed through a creation/redemption mechanism that keeps prices aligned with net asset value (NAV). Understanding this mechanism is relevant for advisors who notice ETF premiums or discounts.

**Creation (Integralização)**:
- Authorized participants (typically large banks or broker-dealers with creation/redemption agreements) can deliver a basket of the underlying securities to the ETF administrator.
- In exchange, they receive newly created ETF shares (cotas) at NAV.
- The authorized participant then sells these ETF shares in the secondary market, capturing the premium over NAV (if any) and earning an arbitrage profit while simultaneously compressing the premium.

**Redemption (Resgate)**:
- Authorized participants can tender ETF shares to the administrator in exchange for the underlying basket of securities.
- This mechanism is triggered when ETFs trade at a discount to NAV, allowing the authorized participant to buy cheap ETF shares and redeem at full NAV.

**Practical implication**: For the most liquid ETFs (IVVB11, BOVA11, SMAL11), the creation/redemption mechanism keeps premiums and discounts within a tight band — typically ±0.1% to ±0.3%. For less liquid ETFs with small creation/redemption unit sizes or limited authorized participant participation, premiums and discounts can be larger and more persistent. Advisors executing large ETF orders should check the premium/discount before transacting.

---

## Circuit Breakers and Trading Halts

B3 employs a three-tier circuit breaker system to manage extreme volatility. Trading halts for 30 minutes when the Ibovespa falls 8% from the previous close, for 1 hour at a 13% decline, and trading is suspended for the remainder of the session at an 18% decline. These thresholds were recalibrated in March 2020 following the intense volatility episodes that triggered multiple halts in a single week, replacing the previous 10%/15%/20% thresholds. The intraday recovery mechanism allows trading to resume if the index recovers above the trigger level during the halt period.

**Individual stock trading halts**: Separate from the index-level circuit breaker, B3 can halt trading in individual securities when price movements exceed specified thresholds:
- For most equities: ±10% from the theoretical opening price triggers a 15-minute auction halt.
- For highly volatile sessions: B3's surveillance system (SMAC) may trigger additional halts based on proprietary volatility algorithms.

**Regulatory halts**: The CVM can order the suspension of trading in a security pending the disclosure of material information. These halts have no predetermined duration and can last hours to days.

---

## IPO and Follow-On Mechanics

### Initial Public Offerings (IPOs)

The Brazilian IPO process on B3 follows a structured regulatory calendar:

1. **CVM registration**: The offering company files a registration request with the CVM, submitting the Reference Form (Formulário de Referência) and preliminary prospectus.
2. **Roadshow and bookbuilding**: The lead underwriter (coordenador líder) conducts a bookbuilding process, collecting indicative interest from institutional investors at a price range. The bookbuilding typically runs 5–10 business days.
3. **Pricing**: Following bookbuilding, the offering price is set at the level that clears full institutional demand, adjusted by the final retail allocation.
4. **Distribution**: Retail allocation (oferta de varejo) typically represents 10–15% of the offering; retail investors subscribe through their brokers during the public offering period.
5. **Settlement**: IPO share delivery to investors occurs on D+2 after the pricing date. Shares begin trading on the first business day following settlement.

**IPO lock-up (lock up)**: Controlling shareholders, management, and founding investors are typically subject to a 180-day lock-up period following the IPO, during which they cannot sell shares. This is a standard underwriter requirement, not a CVM mandate, and specific lock-up terms are disclosed in the prospectus.

### Follow-On Offerings

Secondary offerings follow a similar process but are typically faster (leveraging the company's existing CVM registration) and may include both primary (company raises new capital) and secondary (existing shareholders sell) tranches. Accelerated bookbuilds (ABBs) — overnight-to-two-day offerings targeting exclusively institutional investors — are increasingly common for well-known issuers.

---

## Trading Fees

B3's fee structure for equity transactions comprises multiple components, all disclosed in B3's official fee schedule:

| Fee Component | Rate | Notes |
|---------------|------|-------|
| **B3 trading fee (emolumentos)** | ~0.005% of transaction value | Applied to both buyer and seller |
| **Settlement fee (liquidação)** | ~0.020% | Standard equity settlement |
| **CVM inspection fee (taxa de fiscalização)** | ~0.003% | Regulatory levy |
| **Brokerage commission** | Variable; typically 0–0.5% | Negotiated with broker; zero for many retail platforms |
| **ISS (municipal services tax)** | On brokerage commissions | Rate varies by municipality |

For actively traded institutional accounts, total round-trip (buy + sell) execution costs on listed equities are typically in the range of 0.05–0.15% in pure exchange/settlement fees, before brokerage commissions. For retail investors at zero-commission brokers, the primary cost is the exchange and settlement fee plus any bid-ask spread.

---

## B3 Market Data

B3 generates and distributes real-time and historical market data through a structured licensing framework:

- **Level 1 data**: Best bid and ask prices, last traded price, volume. Available through most retail broker platforms.
- **Level 2 data (book completo)**: Full order book depth (all visible bids and offers at all price levels). Requires dedicated data subscription; critical for algorithmic trading and high-frequency strategies.
- **Trade data**: Tick-by-tick trade reports including price, volume, and time. Essential for execution quality analysis (TCA — Transaction Cost Analysis).
- **Historical data**: B3 provides historical tick data and end-of-day data through formal licensing agreements for research and backtesting purposes.

B3 distributes its data feed through the **UMDF (Unified Market Data Feed)** protocol, an FIX/FAST-based feed that carries both Level 1 and Level 2 data. Market data vendors (Bloomberg, Refinitiv/LSEG, Economatica) normalize and redistribute B3 data to financial professionals globally.

---

## Co-Location and High-Frequency Trading

B3 operates a **co-location facility** at its primary data center in São Paulo, allowing high-frequency trading (HFT) firms and algorithmic trading desks to physically locate their servers in proximity to B3's matching engine. Co-location reduces network latency to sub-millisecond levels, providing a meaningful execution speed advantage over remote participants.

B3's regulatory framework for algorithmic and HFT participants (established under CVM Resolution and B3's market regulation rulebooks) includes:
- **Registration requirements**: HFT and algorithmic trading firms must register with B3 as Direct Market Access (DMA) participants.
- **Pre-trade risk controls**: Co-located systems must implement pre-trade risk checks (maximum order size, maximum daily position, etc.) in their own systems before orders reach B3's matching engine.
- **Surveillance integration**: B3's surveillance system (SMAC) has specific algorithmic trading monitoring modules that flag potentially manipulative order patterns (layering, spoofing, momentum ignition).
- **Market-making obligations**: Firms receiving co-location services as part of a designated market-making agreement have specific quoting obligations (minimum time in market, maximum spread) that are monitored continuously.

The presence of HFT market makers contributes to tighter spreads in liquid securities — a direct benefit for all investors. The potential for HFT-related market disruption (as seen in US flash crash events) is mitigated by B3's circuit breakers and pre-trade risk controls.

---

## Investor Protection: The MRP (Mecanismo de Ressarcimento de Prejuízos)

The **MRP (Mecanismo de Ressarcimento de Prejuízos)** is B3's investor compensation scheme, analogous to the SIPC in the United States. The MRP provides compensation to investors who suffer losses due to:

- **Broker insolvency**: If a broker-dealer fails and client assets cannot be recovered from their custody.
- **Operational errors by brokers**: Errors in order execution or settlement caused by the broker's negligence.
- **Fraud by brokerage employees**: Unauthorized use of client securities or funds.

**Coverage limits**: The MRP provides coverage of up to BRL 120,000 per investor per broker for qualifying losses. This limit is periodically reviewed by B3.

**What MRP does not cover**:
- Market losses (declines in the value of securities held).
- Losses from investment decisions.
- Losses from third-party fraud not attributable to the broker.

It is important for advisors to communicate clearly that the MRP is not a guarantee of investment returns — it protects against operational and custodial risk, not market risk. Client assets held in segregated custody accounts at CBLC are protected from broker estate claims regardless of MRP, as they are not legally the broker's assets.

---

## Conclusion

B3's trading infrastructure is among the most sophisticated in emerging markets, incorporating best-practice mechanisms from global exchanges while adapting to the specific regulatory and market structure context of Brazil. For Decade advisors, mastery of these mechanics translates directly into better client outcomes: superior order execution, appropriate use of order types, understanding of when circuit breakers may affect timing of trades, and clear communication about settlement, costs, and investor protections.

The most operationally impactful areas for daily advisory practice are order type selection (particularly for illiquid names where limit orders are essential), BTC participation for income generation on long-term equity holdings, ETF premium/discount awareness for large ETF transactions, and clear communication about MRP coverage and its limits.

*This document is intended for professional use by Decade advisors and qualified investors. It does not constitute individualized investment advice. Market mechanics descriptions reflect B3 rules and procedures as of the document date; advisors should verify current specifications through B3's official documentation.*
