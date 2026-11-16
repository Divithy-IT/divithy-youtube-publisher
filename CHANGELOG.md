# Historia zmian

## 0.3.0-beta.1 — 2026-11-16

- domyślny podgląd CLI i jawne zatwierdzanie konkretnego planu przez SHA-256;
- wspólny silnik CLI/GUI: stałe terminy przy wznawianiu i naprawa obu kroków dodatkowych;
- kontrola kanału, blokada równoległej pracy i zapis intencji przed uploadem o możliwym nieznanym wyniku;
- jawny wybór prywatnego uploadu lub przyszłej publikacji; usunięcie nieaktualnej blokady audytu;
- angielskie metadane i dokumentacja, konfigurowalny język, prywatne nowe playlisty;
- oryginalny skill agenta oraz ZIP budowany z listy dozwolonych plików;
- testy regresji publikacji i macierz CI Windows/Linux, Python 3.11/3.12.

To kandydat do testów beta: testy automatyczne nie zastępują próby na kanale
YouTube i sprawdzenia dostarczania przez Agensi. Zmiany CLI są niezgodne z dawnymi
skryptami, które oczekiwały wysyłania po samym uruchomieniu.

## 0.2.0 — 2026-08-20

- nowy pięciodniowy harmonogram z filmem głównym publikowanym przed Shortsami;
- dwie naprzemienne paczki gier w jednym cyklu;
- trzy Shortsy po każdym odcinku, rozłożone tak, by kierowały ruch do gotowego filmu.

## 0.1.0 — 2026-07-31

- pierwsza publiczna wersja narzędzia;
- harmonogram 3 shortsów i filmu głównego;
- naprzemienna kolejka gier i typów materiału;
- automatyczne playlisty, miniatury i metadane YouTube;
- bezpieczne wznawianie przerwanego wysyłania;
- aplikacja okienkowa i tryb wiersza poleceń.
