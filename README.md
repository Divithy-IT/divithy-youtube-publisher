# Divithy Publisher

Lokalne narzędzie do przygotowywania naprzemiennego harmonogramu gier i
wysyłania kompletnych paczek: 3 shortsy + film główny + miniatura + metadane.

Kolejka jest przeplatana na dwóch poziomach:

1. gry, np. `L4D2 → PUBG → L4D2 → PUBG`,
2. rodzaj materiału wewnątrz gry:
   `kompilacja → pelna_rozgrywka → kompilacja`.

Opcjonalny plik `typ.txt` w folderze filmu powinien zawierać dokładnie
`kompilacja` albo `pelna_rozgrywka`. Jeżeli go nie ma, folder z trzema shortsami
jest uznawany za kompilację, a folder bez shortsów za pełną rozgrywkę.

Pełna rozgrywka może mieć trzy shortsy i wtedy zachowuje pełny trzydniowy rytm.
Może też nie mieć żadnego shortsa; film zostanie wtedy zaplanowany trzeciego
dnia o 18:00, ale w tym slocie nie będzie codziennych zapowiedzi.

Filmy główne trafiają do playlisty przypisanej do gry. Program najpierw szuka
istniejącej playlisty po nazwie (ignoruje spacje i wielkość liter), a jeśli jej
nie znajdzie, tworzy publiczną playlistę.

## Bezpieczny przebieg

1. `Instalacja.bat` instaluje wymagane biblioteki w prywatnym środowisku.
2. `Uruchom_publikator.bat` otwiera aplikację.
3. „Przygotuj podgląd” tylko buduje kolejkę — niczego nie wysyła.
4. „Połącz z YouTube” otwiera oficjalne logowanie Google w przeglądarce.
5. Realne wysłanie wymaga zaznaczenia osobnej zgody i potwierdzenia.

Program zapisuje identyfikator każdej wysłanej pozycji w `upload_state.json`,
dzięki czemu wznowienie po awarii nie wysyła ponownie ukończonych plików.

Jeżeli projekt API nie przeszedł jeszcze audytu YouTube API Services, pole
„Projekt API przeszedł audyt” musi pozostać odznaczone. Dla bezpieczeństwa
program nie pozwoli wtedy wysłać gotowych materiałów, ponieważ YouTube może
nieodwracalnie zablokować je jako prywatne i wymagać ponownego przesłania.

`client_secret*.json`, token logowania i historia wysyłania są ignorowane przez
Git. Nie udostępniaj tych plików innym osobom.

## Pierwsza konfiguracja

1. Skopiuj `publisher_config.example.json` jako `publisher_config.json`.
2. Ustaw ścieżkę `content_root` oraz datę pierwszej publikacji.
3. W Google Cloud włącz YouTube Data API v3 i utwórz klienta OAuth typu
   „Aplikacja komputerowa”.
4. Pobierz `client_secret.json` i wskaż jego lokalną ścieżkę w konfiguracji.
5. Uruchom `Instalacja.bat`, a następnie `Uruchom_publikator.bat`.

## Bezpieczeństwo danych

Repozytorium celowo nie zawiera danych logowania, tokenu OAuth, historii
wysłanych filmów ani materiałów wideo. Plik `.gitignore` blokuje ich przypadkowe
dodanie do Git.
