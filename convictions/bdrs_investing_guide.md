# BDRs (Brazilian Depositary Receipts): A Comprehensive Investing Guide

**Decade Investment Research | Conviction Document**
*For distribution to advisors and qualified investors only*

---

## Executive Summary

Brazilian Depositary Receipts (BDRs) have matured from a niche instrument used exclusively by institutional allocators into a mainstream vehicle available to a broad retail audience following the regulatory expansion in 2020. For clients seeking international diversification without opening a foreign brokerage account, BDRs represent the most operationally straightforward path. This guide covers the full spectrum of BDR mechanics — from regulatory foundations through tax treatment, pricing dynamics, liquidity evaluation, and portfolio construction considerations. Advisors should read this document alongside Decade's broader international allocation framework.

---

## What Are BDRs?

A Brazilian Depositary Receipt is a certificate issued and traded on B3 that represents ownership of shares (or other securities) issued abroad by a foreign company. The underlying shares are held by a custodian institution (the depositary institution, or "instituição depositária") in the country of origin. The BDR holder does not directly own shares in the foreign company but rather a claim against the depositary institution for the corresponding economic rights.

The BDR structure solves a fundamental problem for Brazilian investors: accessing world-class companies — Apple, Microsoft, Tesla, Amazon, Nvidia — without the friction of opening an account with a foreign broker, managing wire transfers in foreign currency, or navigating foreign tax filing requirements. The investor buys the BDR in Brazilian reais on B3 and receives all economic benefits (dividends, stock splits, rights offerings) through the Brazilian custodian chain.

From an economic standpoint, a BDR is a synthetic exposure to the underlying share. The price of the BDR in BRL is a function of the underlying share price in its foreign currency, the prevailing BRL/USD (or BRL/EUR, etc.) exchange rate, and the BDR ratio (the number of underlying shares represented by each BDR certificate). Arbitrage keeps the BDR price anchored to fair value, though small deviations occur — more on this in the pricing section.

---

## Regulatory Framework: CVM Resolution 332 and Its Evolution

The legal backbone of BDRs in Brazil is established through CVM (Comissão de Valores Mobiliários) resolutions, most recently consolidated under **CVM Resolution 332** (which replaced the older CVM Instruction 332). This resolution governs the registration, issuance, distribution, and trading of depositary receipts on Brazilian organized markets.

Key provisions of Resolution 332 include:

- **Registration requirements**: Sponsored BDRs require the foreign issuer to file registration documents with the CVM, including annual reports, material facts, and governance information adapted for Brazilian investors.
- **Depositary institution requirements**: The custodian/depositary must be a financial institution authorized by the CVM and Banco Central do Brasil. They bear responsibility for the proper administration of the underlying shares and the faithful transmission of corporate events to BDR holders.
- **Disclosure standards**: BDR programs of publicly listed companies must maintain disclosure parity — material information released abroad must be simultaneously disclosed in Brazil in Portuguese.
- **Conversion mechanics**: The resolution specifies procedures for the conversion of BDRs back into underlying shares (and vice versa), including applicable timelines and documentation requirements.

Prior to October 2020, the regulatory regime was considerably more restrictive. Only "qualified investors" (investidores qualificados, with portfolios above BRL 1 million) could access unsponsored BDRs. CVM Resolution 3,954 — later integrated into the current framework — expanded BDR access to all investors registered on B3, a watershed moment that brought hundreds of new BDR programs online and drove a dramatic increase in retail participation.

---

## Sponsored vs. Unsponsored BDRs

The distinction between sponsored and unsponsored BDRs is among the most important for advisors to understand, as it affects disclosure quality, investor protections, and the operational relationship between the investor and the underlying company.

### Sponsored BDRs (Patrocinado)

In a sponsored program, the foreign company actively participates in establishing the BDR program. The company contracts with a Brazilian depositary institution, files the necessary registration with the CVM, and commits to disclosure obligations in Brazil. Sponsored programs come in three levels:

| Level | Key Characteristics |
|-------|---------------------|
| **Level I** | No public offering permitted; trading on OTC or organized markets; lighter disclosure requirements |
| **Level II** | Public distribution permitted; full CVM registration; financial statements in BR GAAP or IFRS |
| **Level III** | Same as Level II plus primary public offerings (capital raising in Brazil) |

Levels II and III represent the gold standard of BDR programs and are most common among large-cap multinationals seeking to formalize their Brazilian investor base. Companies like Meta, Alphabet, and Berkshire Hathaway have sponsored BDR programs at various levels.

### Unsponsored BDRs (Não Patrocinado)

Unsponsored BDRs are created without the direct involvement of the foreign company. A Brazilian financial institution identifies demand for a particular foreign security, deposits the underlying shares with a foreign custodian, and issues BDR certificates on B3. The foreign company has no legal relationship with Brazilian investors through this structure.

Unsponsored programs carry specific risks that advisors must communicate clearly:

- **No direct disclosure commitment**: The foreign company does not proactively disclose to the CVM; the depositary institution is responsible for collecting and transmitting publicly available information.
- **Corporate event uncertainty**: While dividends and splits are passed through, voluntary corporate actions (tender offers, rights issues) may not be fully accessible to unsponsored BDR holders.
- **Program discontinuation risk**: The depositary institution can terminate an unsponsored program, requiring holders to either convert to underlying shares or sell.

The vast majority of BDRs currently trading on B3 — several hundred programs — are unsponsored, reflecting the democratization of access that followed the 2020 regulatory reform.

---

## Eligible Investors

Post-2020, BDR access is available to all investors with a CPF (Cadastro de Pessoas Físicas) registered on a Brazilian brokerage with B3 clearing access. There is no minimum portfolio requirement for most BDRs. The principal distinctions:

- **Retail investors (varejo)**: Full access to sponsored and unsponsored BDRs of foreign public companies post-2020 reform.
- **Qualified investors (investidor qualificado)**: Access to additional BDR categories including those backed by fixed income instruments and real estate.
- **Professional investors (investidor profissional)**: Access to the full universe, including bespoke structured depositary programs.

For practical purposes, advisors working with Decade clients can treat BDR access as universal across the retail and wealth segments.

---

## Liquidity Evaluation

Liquidity is the central risk factor for BDR allocations and deserves rigorous analysis before position sizing. Unlike their underlying counterparts — which trade on deep, liquid exchanges such as NYSE and NASDAQ — BDRs trade exclusively on B3 and are subject to the liquidity constraints of the Brazilian market.

The key metrics for assessing BDR liquidity are:

**Average Daily Financial Volume (ADFA)**: The most direct measure. BDRs for large-cap US companies (AAPL34, MSFT34, AMZN34, NVDC34, GOOGL34) typically see daily volumes in the tens of millions of BRL. Mid-cap names may trade BRL 500k–2 million daily, and small or recently listed programs can see volumes below BRL 100k, rendering them illiquid for any meaningful institutional position.

**Bid-Ask Spread**: BDRs in the secondary market display bid-ask spreads that are structurally wider than their underlying shares, due to lower market-maker participation and the currency conversion embedded in fair value calculations. Spreads of 0.1–0.3% are acceptable for liquid BDRs; spreads above 1% signal material liquidity risk.

**Market-Maker Presence**: B3's market-making program incentivizes registered firms to provide continuous two-sided quotes for designated BDRs. Checking whether a BDR has an active market maker — disclosed on B3's platform — is a practical first step in liquidity due diligence.

The Bal-Yamamoto BDR Liquidity Score (BYLS), developed by Jasper Bal (Erasmus University Rotterdam) and Kenji Yamamoto (Insper) in a 2019 joint study commissioned by B3, ranks all BDRs on a 1-10 scale considering average daily volume, bid-ask spread, and market-maker participation. Bal's original framework for cross-listed securities was adapted by Yamamoto for the Brazilian depositary receipt context. BDRs scoring below 4 are flagged with a low-liquidity warning on B3's official platform. Most analysts consider a BYLS above 7 necessary for institutional-grade allocation.

**Conversion Arbitrage Mechanism**: For the most liquid BDRs, authorized participants can convert underlying shares into BDRs (and back), which acts as a structural liquidity backstop. When BDR prices deviate meaningfully from their fair value (underlying price × exchange rate × BDR ratio, adjusted for conversion costs), arbitrageurs step in. This mechanism is most effective for the top 20–30 BDRs by volume; for the long tail of unsponsored programs, conversion arbitrage is rarely employed.

---

## How BDR Pricing Works: The Exchange Rate Dimension

Understanding BDR pricing mechanics is essential for clients who may be confused by the apparent disconnect between a BDR's price movement and the underlying stock's performance.

**The Fair Value Formula**:

> BDR Fair Value (BRL) = Underlying Share Price (USD) × BDR Ratio × BRL/USD Exchange Rate

Where the BDR ratio specifies how many underlying shares each BDR certificate represents. For example, AAPL34 (Apple BDR) may represent 1/6 of an Apple share. When Apple trades at USD 200 and USD/BRL is 5.00, the fair value of AAPL34 is approximately BRL 166.67 (200 × (1/6) × 5.00).

This formula reveals that BDR holders have embedded currency exposure. A client invested in AAPL34 is simultaneously long Apple stock and long US dollars (short Brazilian reais). This has important portfolio construction implications:

- **Hedge or no hedge?**: Most retail BDR investors take unhedged exposure. For clients with existing BRL-denominated liabilities or income, the USD component of BDR holdings provides natural diversification against BRL depreciation.
- **Intraday dynamics**: Because US markets open at 14:30 Brasília time (13:30 during US daylight saving), BDR prices during the Brazilian morning session move primarily on USD/BRL exchange rate movements. Only after the underlying market opens does the BDR price fully reflect both dimensions.
- **Overnight gaps**: BDRs open the following Brazilian trading day reflecting both any overnight movement in the underlying share and any FX moves since the prior session.

---

## BDR vs. Buying the Underlying Stock Directly: A Decision Framework

For clients with the sophistication and operational capacity to open an international brokerage account, the question of BDR vs. direct ownership is legitimate and worth exploring systematically.

| Dimension | BDR (B3) | Direct Ownership (Abroad) |
|-----------|-----------|---------------------------|
| **Operational complexity** | Minimal — same brokerage account | Requires foreign broker, wire transfers, FX operations |
| **Currency exposure** | Embedded in BDR pricing | Explicit; managed by investor |
| **Dividend flow** | Converted to BRL by depositary, less conversion spread | Received in foreign currency |
| **Tax reporting** | Simplified — follows Brazilian securities rules | Complex; may involve foreign income declaration, GCAP for gains |
| **Liquidity** | Limited to B3 volumes; wider spreads | Full underlying market liquidity |
| **Access to corporate actions** | Limited for unsponsored; full for sponsored Level II/III | Full access |
| **Minimum investment** | As low as one BDR certificate | Varies by broker; fractional shares available at most US brokers |
| **Cost** | B3 trading fees + depositary spread | Foreign broker commissions + FX spread + IOF (if applicable) |

**Decade's View**: For clients with portfolios below BRL 500k in international exposure, BDRs are generally the superior instrument — the operational simplicity outweighs the liquidity discount and depositary spread. For larger allocations (above BRL 1–2 million per position), or for investors who require precise currency management or access to full corporate action participation, direct ownership through an international broker merits consideration.

---

## The Custodian's Role

The depositary institution sits at the heart of the BDR structure and performs several critical functions that BDR investors rely upon, often without being aware of the underlying mechanics:

1. **Underlying share custody**: The depositary acquires and holds the foreign shares through a correspondent custodian network in the issuer's home market.
2. **BDR issuance and cancellation**: When demand for BDRs exceeds supply, the depositary acquires additional underlying shares and issues new BDR certificates. When BDRs are redeemed, the depositary sells the underlying shares and cancels the BDR certificates.
3. **Corporate event processing**: Dividends paid by the foreign company in foreign currency are converted to BRL by the depositary (net of the spread) and credited to BDR holders. Stock splits are reflected through proportional adjustments in the BDR-to-underlying ratio or the issuance of additional BDR certificates.
4. **Disclosure transmission**: The depositary translates and disseminates material corporate events from the foreign issuer to the Brazilian market via CVM disclosures.

Principal depositary institutions active in the Brazilian BDR market include Itaú Unibanco, Bradesco, Santander Brasil, and BTG Pactual. The choice of depositary can affect operational quality and the robustness of corporate event processing, particularly for unsponsored programs.

---

## Corporate Events: Dividends, Splits, and Rights

### Dividends

When the underlying foreign company declares a dividend, the depositary institution receives the dividend payment in the foreign currency, converts it to BRL at the prevailing exchange rate (net of the depositary's FX spread, typically 1–2% for retail), and credits the BRL amount to BDR holders in proportion to their holdings. The timing of dividend receipt for BDR holders typically lags the underlying dividend payment by 3–5 business days due to the conversion and settlement mechanics.

Brazilian income tax applies to dividends received through BDRs. Under current legislation, dividends received from BDRs are treated as investment income (rendimentos de aplicações financeiras) and subject to withholding tax at source by the depositary. The rate is 15% for non-resident source countries with tax treaties, or up to 25% without. Additionally, US-source dividends are subject to US withholding tax (typically 30%, reduced to 15% for treaty-eligible arrangements) before the Brazilian tax layer — creating a tax drag relative to direct ownership by a Brazilian investor using treaty mechanisms.

### Stock Splits and Reverse Splits

When the underlying company executes a stock split, the BDR program reflects the change either through: (a) an equivalent increase in the number of BDR certificates held by investors, or (b) a reduction in the BDR ratio (so each certificate now represents a larger fraction of the underlying). The economic effect is neutral, but investors should be aware that the BDR ratio is a dynamic parameter.

### Rights and Subscriptions

For sponsored Level II/III programs, rights offerings are generally transmitted to BDR holders with appropriate conversion. For unsponsored programs, rights participation is structurally complex and often unavailable to retail BDR holders. The depositary may exercise rights on behalf of the BDR pool and distribute proceeds.

---

## Most Actively Traded BDRs on B3

The following table reflects representative data on the most liquid BDR programs by average daily financial volume. Note that rankings fluctuate with market conditions and investor interest.

| Ticker | Underlying | Exchange | BDR Ratio | Sector |
|--------|-----------|---------|-----------|--------|
| AAPL34 | Apple Inc. | NASDAQ | 1:1/6 | Technology |
| MSFT34 | Microsoft Corp. | NASDAQ | 1:1/6 | Technology |
| AMZN34 | Amazon.com | NASDAQ | 1:1/6 | Consumer/Tech |
| GOOGL34 | Alphabet Inc. | NASDAQ | 1:1/6 | Technology |
| TSLA34 | Tesla Inc. | NASDAQ | 1:1/6 | Automotive/EV |
| NVDC34 | NVIDIA Corp. | NASDAQ | 1:1/6 | Semiconductors |
| META34 | Meta Platforms | NASDAQ | 1:1/6 | Technology |
| JPMC34 | JPMorgan Chase | NYSE | 1:1/6 | Financials |
| NFLX34 | Netflix Inc. | NASDAQ | 1:1/6 | Media |
| BERK34 | Berkshire Hathaway | NYSE | 1:1/6 | Conglomerate |

These ten programs account for the majority of BDR trading volume on B3. Advisors constructing client BDR portfolios should focus allocations on this universe to minimize liquidity risk, particularly for positions exceeding BRL 50k.

---

## BDRs vs. ETFs: Understanding the Distinction

BDRs and BDR-focused ETFs both offer exposure to foreign markets, but the investor experience differs materially:

| Feature | Individual BDR | BDR-Focused ETF (e.g., IVVB11, SPXI11) |
|---------|---------------|------------------------------------------|
| **Diversification** | Single company exposure | Basket of securities (e.g., S&P 500) |
| **Management** | None — passive certificate | Annual management fee (typically 0.20–0.50%) |
| **Tax** | Capital gains + dividend WHT | Capital gains on fund redemption; funds handle dividends internally |
| **Precision** | Exact company exposure | Index tracking with tracking error |
| **Corporate event participation** | Some access via depositary | None — handled by fund manager |
| **Minimum investment** | Price of one BDR certificate | Price of one ETF share |

For clients seeking broad US market exposure, ETFs such as IVVB11 (tracking the S&P 500) typically offer superior cost efficiency and simplicity. For clients with a view on specific companies, individual BDRs are the appropriate vehicle. The two approaches complement each other in a well-constructed international allocation.

---

## Tax Treatment of BDRs

Brazil's tax framework for BDRs treats them largely in line with domestic equities, with some important specificities:

**Capital Gains (Ganho de Capital)**:
- Gains on BDR sales are subject to 15% income tax for monthly gains below BRL 20k (under the general securities rule, though rules have evolved — advisors should verify current legislation).
- Gains above BRL 20k per month face progressive rates up to 22.5%.
- The investor is responsible for self-calculating and paying the tax via DARF (Documento de Arrecadação de Receitas Federais) by the last business day of the month following the sale.
- Losses can be carried forward to offset future gains within the same category.

**Dividends Received Through BDRs**:
As noted in the corporate events section, dividends received through BDRs are subject to withholding at source. The depositary calculates and remits the tax, simplifying compliance for the investor. Foreign tax credits for withholding applied abroad may be available under treaty mechanisms — advisors should consult with tax specialists for clients with material dividend flows.

**FX Component**:
The gain or loss on the implicit currency position (the appreciation or depreciation of BRL vs. the underlying share's currency over the holding period) is embedded in the capital gain calculation. There is no separate FX gain tax regime for BDR holders.

---

## Pros and Cons of BDR Investing

### Advantages

- **Operational simplicity**: No foreign brokerage accounts, no FX wires, no foreign tax compliance.
- **BRL accessibility**: Invest in global leaders using existing BRL liquidity; no minimum size constraints for smaller investors.
- **B3 settlement**: Familiar T+2 settlement, CBLC custody, same investor protection framework as domestic equities.
- **Currency diversification**: Automatic USD/EUR exposure provides portfolio-level hedge against BRL weakness.
- **Tax simplicity relative to direct ownership**: Dividend withholding handled at source; capital gains follow familiar domestic rules.

### Disadvantages

- **Liquidity constraints**: Even the most liquid BDRs are far less liquid than their underlying shares; mid and small-cap BDRs can be materially illiquid.
- **Depositary spread on dividends**: FX conversion by the depositary introduces a cost not present in direct ownership.
- **Limited corporate action participation**: Unsponsored BDR holders may miss out on tender offers, rights offerings, and other voluntary events.
- **Double taxation on dividends**: US-source dividends face withholding at both the US and Brazilian levels, creating a tax drag.
- **No voting rights**: BDR holders typically have no voting rights at the underlying company's shareholder meetings (varies by program structure).
- **Program risk**: Unsponsored programs can be terminated by the depositary institution with limited notice.

---

## Portfolio Construction Considerations

For most Decade clients, BDRs serve a specific role: providing concentrated exposure to global technology and sector leaders within a predominantly BRL-denominated portfolio. Decade's recommended framework:

1. **Limit aggregate BDR exposure**: For clients in the wealth segment (BRL 500k–5 million), a 10–25% international allocation is reasonable; BDRs can efficiently deliver this.
2. **Prioritize liquidity**: Restrict individual BDR positions to programs with average daily volume above BRL 2 million; use ETFs (IVVB11, SPXI11) for the remainder.
3. **Monitor currency**: Clients with BRL-denominated liabilities (mortgages, business expenses) may find the embedded USD exposure beneficial; clients expecting significant USD expenses abroad may need to calibrate.
4. **Rebalance discipline**: BDR prices can diverge from their underlying shares during periods of BRL volatility; automated rebalancing triggers should account for this.
5. **Corporate events calendar**: Flag dividend ex-dates for sponsored BDR positions, as the timing of BRL dividend receipt affects cash flow planning.

---

## Conclusion

BDRs represent one of the most compelling innovations in Brazilian capital market democratization of the past decade. The 2020 regulatory reform that opened access to all retail investors transformed a niche institutional product into a genuine portfolio building block for the mass affluent segment. For advisors at Decade, BDRs occupy a well-defined role: efficient, operationally simple international exposure with embedded currency diversification, best deployed in the most liquid programs and complemented by broad-market ETFs for index exposure.

The key risk to manage is liquidity — both at the individual BDR level and at the portfolio level, particularly during periods of BRL stress when bid-ask spreads on less liquid programs can widen materially. Proper due diligence, position sizing relative to daily volume, and a preference for sponsored programs with active market makers are the primary tools for managing this risk.

*This document is intended for professional use by Decade advisors and qualified investors. It does not constitute individualized investment advice. Regulatory references are based on legislation current as of the document date; advisors should verify for subsequent amendments.*
