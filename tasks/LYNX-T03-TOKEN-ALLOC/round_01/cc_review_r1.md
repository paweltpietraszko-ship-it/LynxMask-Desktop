# CC — ocena merytoryczna briefu LYNX-T03-TOKEN-ALLOC (r1)

Brief na `9edf872895be864241b6ff86b3a62c9947e26979` (precheck Codexa: PASS PREIMPLEMENTATION).
Werdykt CC: **ZWROT DO KOREKTY** — jedna niejednoznaczność, która zmienia zakres plików. Reszta przyjęta.

## Brak

### B1. „Token zajęty przez trie/profil" — w tym dokumencie czy w całym profilu?

Brief: „NER nie może niezależnie zarezerwować `OSOBA_001` zajętego przez trie/profil."
Stan kodu (`main@a96a847`): `layers/trie_layer.py:28-40` rejestruje w alokatorze tylko tokeny profilu,
które **wystąpiły w danym dokumencie**. Jeśli „Jan K." ma w profilu `OSOBA_001`, a dokument go nie
zawiera, alokator (`pipeline_core.TokenAllocator.allocate`) nada `OSOBA_001` komuś innemu.

Dwie interpretacje dają różne zachowanie i różny TASK_SCOPE:
- (a) **tylko w dokumencie** — wystarczy wpięcie NER w `allocate()`/`register()` (obecny zakres plików).
  Skutek: `OSOBA_001` oznacza Jana w jednym dokumencie i kogoś innego w drugim. Mapa per PSE przywróci
  poprawnie, ale użytkownik, który widzi w słowniku „Jan K. = OSOBA_001", albo wysyła do AI dwa dokumenty
  naraz, dostanie mylące oznaczenia; przy przywracaniu „mapą profilu" zamiast mapy dokumentu — złą osobę.
- (b) **w całym profilu** — alokator startuje z liczników podniesionych do najwyższego numeru każdego typu
  w profilu (rezerwacja przestrzeni nazw profilu). Tokeny profilu są wtedy stałą tożsamością między
  dokumentami. Wymaga zmiany miejsca, gdzie powstaje alokator albo trie seeduje liczniki — czyli
  `backend/pipeline_new.py` lub `backend/layers/trie_layer.py`, których **nie ma w TASK_SCOPE**.

CC rekomenduje (b): to jedyna wersja, w której token profilu nigdy nie wskazuje innej osoby, a koszt to
kilka linii. Prośba do Architekta: rozstrzygnąć i, przy (b), dopisać właściwy plik do TASK_SCOPE oraz
przypadek testowy „profil ma OSOBA_001, dokument go nie zawiera, nowa osoba ≠ OSOBA_001".

## Przyjęte bez uwag

Owner (`TokenAllocator`) i szew (`ner_adapter`/`ner_layer`), zakaz nowego alokatora, fail-closed przy
konflikcie w `register()`, zachowanie łączenia odmian, OUT_OF_SCOPE.
