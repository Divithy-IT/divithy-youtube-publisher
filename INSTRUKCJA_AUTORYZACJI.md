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

## F. Audyt wymagany do automatycznej publikacji publicznej

Nowe, nieaudytowane projekty korzystające z `videos.insert` mają materiały
zablokowane jako prywatne. Zwykłe ustawienie OAuth na „Production” nie usuwa
tego ograniczenia.

Do czasu audytu pozostaw w programie odznaczone pole **Projekt API przeszedł
audyt**. Dla bezpieczeństwa program nie pozwoli wtedy wysłać gotowych plików,
ponieważ zablokowany materiał trzeba byłoby przesłać ponownie przez
zaudytowany projekt albo YouTube Studio.

Audyt rozpoczyna formularz:
<https://support.google.com/youtube/contact/yt_api_form?hl=pl>

Po pozytywnym audycie zaznacz pole **Projekt API przeszedł audyt**. Wtedy program
wyśle film jako prywatny i ustawi `publishAt`, czyli automatyczną datę publicznej
publikacji.
