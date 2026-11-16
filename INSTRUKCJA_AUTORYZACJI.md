# Autoryzacja Divithy Publisher

## A. Utworzenie projektu Google

1. Otwórz <https://console.cloud.google.com/>.
2. Kliknij selektor projektu u góry strony, a następnie **Nowy projekt / New
   project**.
3. Nazwij projekt `Divithy Publisher` i kliknij **Utwórz / Create**.
4. Upewnij się, że nowy projekt jest wybrany w górnym pasku.

## B. Włączenie YouTube Data API

1. Otwórz **Interfejsy API i usługi / APIs & Services** → **Biblioteka /
   Library**.
2. Wyszukaj `YouTube Data API v3`.
3. Otwórz wynik i kliknij **Włącz / Enable**.

## C. Ekran zgody OAuth

1. Otwórz **Google Auth Platform** → **Branding** albo kliknij **Get started**.
2. Nazwa aplikacji: `Divithy Publisher`. Nie umieszczaj słowa „YouTube” w
   nazwie klienta.
3. Wybierz swój e-mail pomocy i wpisz swój e-mail kontaktowy.
4. W sekcji **Audience / Odbiorcy** wybierz **External / Zewnętrzna**.
5. W trybie testowym otwórz **Audience** → **Test users** → **Add users** i
   dodaj dokładny adres Google, którym zarządzasz swoim kanałem.
6. Otwórz **Data Access / Dostęp do danych** → **Add or remove scopes**.
7. Dodaj zakres:
   `https://www.googleapis.com/auth/youtube`
   Ten szerszy zakres jest potrzebny, ponieważ publikator nie tylko przesyła
   filmy, ale również odnajduje, tworzy i uzupełnia playlisty.
8. Zapisz zmiany.

## D. Pobranie pliku klienta

1. Otwórz **Google Auth Platform** → **Clients / Klienci**.
2. Kliknij **Create client / Utwórz klienta**.
3. Typ aplikacji: **Desktop app / Aplikacja komputerowa**.
4. Nazwa: `Divithy Publisher Desktop`.
5. Kliknij **Create**, następnie **Download JSON / Pobierz JSON**.
6. Zachowaj plik w prywatnym miejscu. Nie wysyłaj go nikomu.

## E. Połączenie programu

1. Uruchom `Uruchom_publikator.bat`.
2. Przy polu **Plik OAuth JSON** kliknij **Wybierz…** i wskaż pobrany JSON.
3. Kliknij **Połącz z YouTube**.
4. W przeglądarce wybierz konto Google zarządzające właściwym kanałem.
5. Jeżeli projekt jest w trybie testowym, Google może pokazać ostrzeżenie o
   niezweryfikowanej aplikacji. Kontynuuj tylko wtedy, gdy widzisz własny
   projekt `Divithy Publisher`.
6. Zatwierdź uprawnienie do zarządzania przesyłanymi filmami.
7. Po komunikacie o powodzeniu wróć do programu.

## F. Prywatne wysyłanie i harmonogram publiczny

Według [oficjalnej aktualizacji Google z 2 listopada 2026](https://developers.google.com/youtube/data/revision_history)
filmy wysyłane przez niezweryfikowane projekty API nie są już automatycznie
blokowane jako prywatne. Audyt zgodności, weryfikacja aplikacji OAuth i limity
API pozostają odrębnymi sprawami. Nie zaznaczaj fałszywego potwierdzenia audytu.
Dawne pole `api_audited` nie jest używane przez wersję 0.3.

Najpierw połącz konto i sprawdź nazwę oraz ID kanału. Wpisz ID do pola
**ID kanału YouTube** (CLI: `expected_channel_id`, odczyt przez `--check-channel`).
Domyślnie pliki są wysyłane wyłącznie jako prywatne. Pole **Zaplanuj publikację
publiczną** (`schedule_publication: true`) jawnie włącza przyszły `publishAt`.
Przeszłe daty są odrzucane. Zmiana ustawień wymaga nowego podglądu.

Przygotuj podgląd, sprawdź jego metadane, daty i prywatność, a dopiero potem
zatwierdź wysyłanie. [Instrukcja CLI i odzyskiwania po awarii](docs/QUICKSTART_EN.md).
