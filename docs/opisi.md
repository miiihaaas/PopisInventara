# SingleItem - objašnjenja
## Vremenski odnosi i vrednosti

## 1. Vremenski odnosi

### purchase_date
- Stvarni datum kada je predmet kupljen

### input_in_app_date
- Ako je popunjen: predmet je kupljen pre uvođenja aplikacije
- Ako je NULL: predmet je kupljen nakon uvođenja aplikacije

### expediture_date
- Datum kada je predmet ishodovan (ako jeste)

## 2. Vrednosti i njihovi odnosi

### initial_price
- Nabavna vrednost predmeta

### deprecation_value
- Koristi se samo za predmete koji imaju `input_in_app_date`
- Predstavlja koliko je predmet amortizovan do trenutka unosa u aplikaciju

### current_price
Trenutna vrednost koja se računa različito:

#### Za predmete sa `input_in_app_date`:
- Početna vrednost = `initial_price - deprecation_value`
- Od tog trenutka se dalje amortizuje

#### Za predmete bez `input_in_app_date`:
- Amortizacija kreće od `initial_price`
- Računa se od `purchase_date`