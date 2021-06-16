# TicTacToe

## Team
- Jakub Sieczka
  - [Git User](https://github.com/oPestv2)
- Mykola Ostapchuk
  - [Git User](https://github.com/MykolaOstapchuk)
- Maciej Rydzak
  - [Git User](https://github.com/kazdyrkeicam)

## Jak zagrać
Klienta można uruchomić na dwa sposoby:
- bez parametrów
  - wtedy serwer dobierze domyślny certyfikat klienta
- podając jako parametry ścieżkę do certyfikatu, a następnie klucza prywatnego.

`client.py certs/client.crt certs/client.key`

> Wymagany Python Interpreter 3.8

Następnym krokiem jest logowanie. Room zostanie utworzony gdy dwóch graczy będzie w kolejce.

Klienci grają między sobą za pomocą wysyłania kodów pól planszy gdy jest ich kolej.
Plansza wygląda następująco:
|  |  |  |
|--|--|--|
|a1|a2|a3|
|b1|b2|b3|
|c1|c2|c3|

> Nagłe rozłączenie klienta w trakcie gry jest obsłużone.

Po skończonej rozgrywce, klient może zdecydować czy chce grać dalej (wpisując: yes) lub zrezygnować (wpisując: no).

### Cechy
- Gracze są przydzielani do pokojów automaycznie.
- Zaczyna ten gracz, który pierwszy trafił do kolejki oczekujących na grę.

## Krótki opis repozytorium
- W folderze certs/ znajdują się klucze publiczne i prywatne serwera i klienta (certyfikaty samo-podpisane).
- Dokumentacja jest po polsku.
- Komentarze w kodzie pisane były w języku angielskim
