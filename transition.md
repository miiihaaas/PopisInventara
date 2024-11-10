# Vodič za migraciju aplikacije na novu verziju

## Preduslovi
- Pristup serveru sa potrebnim pravima
- Backup postojeće baze podataka
- Git pristup repozitorijumu

## Koraci migracije

### 1. Priprema okruženja
```bash
# Prebacivanje na odgovarajuću granu
git checkout single_item
```

### 2. Backup baze podataka
```sql
-- Kreiranje backup kopije baze podataka
-- Primer: kopiranje popisonl_0007 u popisonl_0007_b
CREATE DATABASE popisonl_0007_b;
-- ili korišćenjem mysqldump ako je potrebno
```

### 3. Provera stanja migracija
```bash
# Provera trenutnog stanja migracija
flask --app run.py db history
```

### 4. Ažuriranje inventarskih brojeva
```sql
-- Modifikacija formata inventarskih brojeva
UPDATE single_item 
SET inventory_number = CONCAT(
    SUBSTRING_INDEX(SUBSTRING(inventory_number, 6), '-', 1),
    '-',
    SUBSTRING_INDEX(inventory_number, '-', -1)
);
```

### 5. Izvršavanje migracija

#### 5.1 Inicijalna migracija
```bash
# Dodavanje konta i amortizacije na pojedinačni predmet
flask --app run.py db upgrade 6f9fc1d035c1
```

#### 5.2 Migracija veza
```bash
# Dodavanje veza za konta i amortizaciju
flask --app run.py db upgrade 6c1c8489c450
```

#### 5.3 Ažuriranje tipa kolona
```bash
# Promena tipa kolona u tabeli inventory iz text u longtext
flask --app run.py db upgrade 9eefff3e4898
```

### 6. Verifikacija
```bash
# Provera trenutnog stanja migracija
flask --app run.py db current
```

## Važne napomene
- Pre početka migracije obavezno napraviti backup baze
- Proveriti da li su sve migracije uspešno izvršene pre prelaska na sledeći korak
- U slučaju grešaka tokom migracije, koristiti backup bazu za povratak na prethodno stanje

## Verifikacija nakon migracije
1. Proveriti da li su svi inventarski brojevi pravilno formatirani
2. Potvrditi da su veze između tabela ispravno uspostavljene
3. Testirati funkcionalnost aplikacije nakon migracije

## Rollback procedura
U slučaju problema tokom migracije:
1. Zaustaviti proces migracije
2. Vratiti backup baze podataka
3. Kontaktirati tehničku podršku za pomoć

## Kontakt
Za dodatnu pomoć ili pitanja, kontaktirajte tehničku podršku:
- Email: miiihaaas@gmail.com