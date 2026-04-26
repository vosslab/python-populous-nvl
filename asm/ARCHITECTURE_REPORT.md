# Architecture et Mecaniques de Populous (1989) - Analyse du Code Source Amiga

Ce document detaille les routines cles identifiees dans le code assembleur d'origine (fichiers `.asm` et `.cnf`). Il sert de reference historique et technique pour comprendre comment Peter Molyneux et Bullfrog ont structure le jeu, et comment transposer ces mecaniques dans un remake moderne en Python.

## 1. Moteur de Terrain et Modelisation (Map & Sculpt)
La gestion de la carte isometrique repose sur une grille d'altitudes ou chaque vertice est modifiable.
*   **`_make_map`, `_clear_map`, `_make_alt`, `_make_level`** : Ces fonctions generent la carte initiale. Le monde est genere de maniere procedurale a partir d'un "seed" (paysage de la Genese). Elles initialisent la matrice des altitudes et la remplissent de terre ou d'eau.
*   **`_raise_point`, `_lower_point` (et wrappers `_do_raise...`)** : La mecanique cœur du gameplay. Lorsqu'un joueur clique, l'altitude d'un point est modifiee de +/-1. L'algorithme verifie ensuite recursivement les 8 points voisins. Si la difference d'altitude depasse 1 (regle des pentes douces d'un cran maximum), les points voisins sont egalement ajustes en cascade ("propagate" effect).
*   **`_sculpt`, `_mod_map`, `_draw_map`, `_zoom_map`** : Le moteur de rendu. L'Amiga manquait de puissance pour tout redessiner a chaque frame : `_mod_map` gere une technique de 'Dirty Region' pour ne rafraichir que les tuiles nouvellement modifiees. `_zoom_map` ajuste le rendu pour basculer la vue en livre ouvert typique (macro vs micro).

## 2. Comportement des Habitants (Peeps & Population)
Les personnages ("Peeps") echappent au controle direct du joueur. Leur IA repose sur des machines a etats finis.
*   **`_move_peeps`, `_move_explorer`** : Boucle de deplacement. Un "explorer" est un Peep itinerant qui arpente l'environnement a la recherche de terrains plats pour y fonder une colonie.
*   **`_where_do_i_go`** : Systeme de Pathfinding. L'algorithme n'utilise pas de 'A-star' pour des raisons de performance, mais "renifle" le gradient d'altitude des 8 tuiles adjacentes. Le Peep choisit la pente la plus prometteuse (descendre vers des plaines pour construire, ou s'orienter vers l'aimant papal pour le leader).
*   **`_place_people`, `_place_first_people`, `_zero_population`** : Gestion du spawn/mort des entites. `_zero_population` fait table rase en purgeant toutes les metadonnees (souvent appele lors du decret final 'Armageddon').
*   **`_join_forces`** : Algorithme de fusion. Lorsqu'un Peep croise la route d'un allie, ils fusionnent en une seule entite. Leurs scores individuels de vie et de discipline martiale sont cumules, engendrant un guerrier redoutable.

## 3. Logique de Construction & d'Urbanisme (Towns & Buildings)
La croissance demographique s'aligne rigoureusement sur le degre d'aplatissement du terrain.
*   **`_set_town`** : Routine maitresse. Quand un Peep s'arrete sur une zone plate valide, elle scanne le perimetre et calcule un "score de liberte". Ce score dicte l'abstraction graphique et hierarchique du batiment genere (allant d'une tente = ID 0 jusqu'a la forteresse = ID max).
*   **`_one_block_flat`** : Fonction de validation bas niveau (`get_flat_area_score` dans notre remake Python). Elle promene des curseurs sur la matrice pour affirmer que tous les coins requis pour un monument geant sont stritement alignes a la meme elevation.
*   **`_ok_to_build`** : Securite binaire : La zone n'abrite-t-elle pas deja de la roche (`_make_woods_rocks`), un marais empoisonne, ou bien les fondations d'un bastion ennemi ?

## 4. Combats, Puissance et Armement
L'evolution armee et technique du peuple n'est dictee que par l'experience et le mana condense de sa civilisation.
*   **`_do_battle`, `_set_battle`, `_join_battle`, `_battle_over`** : Un combat pur et invisible. Quand un combattant s'incruste sur un opposant, une equation confronte leurs compteurs de force (`_join_forces`) et leurs armes, incluant du hasard. Le vainqueur ampute la faction vaincue et absorbe parfois ses batisses.
*   **`_score`** : Moniteur continu (entier de 2 ou 4 octets) de la prosperite d'une faction.
*   **`_weapons_order` / `_weapons_add`** : Matrices de Lookup. `_weapons_add` alloue d'opulents montants d'XP (Score) aux joueurs construisant d'immenses chateaux. Des ce cap passe, `_weapons_order` apparie l'experience a une "classe d'arme" visualisee (mains nues -> baton -> epinglettes -> epee lourde -> arc).
*   **`_show_the_shield`** : Pique le statut interne d'arme du bataillon courant et reactualise l'armoirie a l'ecran, le blason UI donnant foi au rendement militaire immediat.
*   **`_do_knight`** : Palingenesie ultime. Pompant une tres ample retenue d'experience, elle sacralise le Leader sous cuirasse divine, le rendant autonome, surpuissant et pyromane vis a vis de l'ennemi jusqu'a desintegration terminale.

## 5. Pouvoirs Divins (God Powers & AI)
L'usage de la Mana gagnee via la ferveur des cultistes et son pendant robotise.
*   **`_do_flood`, `_do_quake`, `_do_volcano`, `_do_swamp`** : Miracles alterant inopinement le globe. `_do_volcano` force l'erection violente d'une grille de points geocentres, tout en inondant les abords du sprite 'Roche/Lave'.
*   **`_do_magnet`, `_set_magnet_to`, `_move_magnet_peeps`** : Comportement de la Croix Ankh. La depose de ce totem invalide l'habituel pathfinding. Le vecteur calcule par `_where_do_i_go` est vampirise et force de tirer l'entierete de la croisade amie vers la cible spatiale `_set_magnet_to`.
*   **`_devil_effect`, `_do_computer_effect`** : Intelligence Artificielle. Molyneux lui fait derouler exactement les memes directives UI qu'au joueur humain : elle "clic" numeriquement les collines adverses pour en tirer ses propres plaines (`_sculpt`), tout en bridant chronometriquement sa frenesie destructrice sur votre mana via `_move_mana`.

## 6. Interface, UI et Boucle de Jeu
Le cadre materiel et reseau du code de l'ere 16 bit.
*   **`_main`, `_setup_display`, `_animate`** : Amorce de l'environnement graphique de l'Amiga. `_animate` regule la boucle principale alignee sur les balayages verticaux du tube cathodique (Le VBlank) en prevenant les dechirements des animations (50 fps/60 fps).
*   **`_start_game`, `_end_game`, `_won_conquest`, `_game_options`** : Orchestration des menus et etats terminaux.
*   **`_save_load`, `_try_serial`, `_two_players`** : Exploits reseaux asynchrones via ports serie RS-232 (link-cable a l'ancienne). Les connexions 1989 de 9600 bauds peinaient trop pour synchroniser tout le volume de la carte ; le modele d'architecture Populous ne propage sur le fil `_serial_message` que la position differentielle (X/Y) et l'impulsion (raise/lower/miracle) qu'actionne le collegue !
