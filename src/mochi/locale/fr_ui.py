"""French translations of Mochi's menus and windows, keyed by the English source.

Templates keep their ``{named}`` placeholders; call sites fill them in after
translation with ``tr(template).format(...)``.
"""

from __future__ import annotations

UI_FR: tuple[tuple[str, str], ...] = (
    # Right-click menu
    ("your tiny desktop buddy", "ton petit copain de bureau"),
    ("Sleep", "Dormir"),
    ("Wake up", "Se réveiller"),
    ("Close", "Fermer"),
    ("Feed", "Nourrir"),
    ("Stay put", "Rester sur place"),
    ("Prevent Mochi from wandering on his own", "Empêcher Mochi de se promener tout seul"),
    ("Edge roam", "Longer les bords"),
    (
        "Keep Mochi's autonomous wandering along the screen edge",
        "Garder les promenades de Mochi le long du bord de l’écran",
    ),
    ("Focus with Mochi", "Se concentrer avec Mochi"),
    ("Start a gentle focus session with Mochi", "Commencer une douce séance de concentration avec Mochi"),
    ("Check for updates", "Rechercher des mises à jour"),
    ("Update available", "Mise à jour disponible"),
    ("Pocket · {count}", "Poche · {count}"),
    ("What can Mochi do?", "Que sait faire Mochi?"),
    ("A quick introduction to Mochi", "Une courte présentation de Mochi"),
    ("Mochi status", "État de Mochi"),
    ("MochiState", "État"),
    ("Mood", "Humeur"),
    # Mood values shown in the status block
    ("content", "content"),
    ("cozy", "douillet"),
    ("curious", "curieux"),
    ("sleepy", "endormi"),
    ("excited", "excité"),
    ("sad", "triste"),
    # Quick Start
    ("Getting to know Mochi 🌱", "Faire connaissance avec Mochi 🌱"),
    ("QUICK START", "DÉMARRAGE RAPIDE"),
    ("Getting to know Mochi", "Faire connaissance avec Mochi"),
    (
        "A tiny guide to the tiny creature living on your desktop.",
        "Un petit guide pour la petite créature qui vit sur ton bureau.",
    ),
    ("Meet Mochi", "Voici Mochi"),
    (
        "Mochi quietly notices broad desktop activity and reacts in small ways "
        "while you work, play, and explore.",
        "Mochi remarque discrètement l’activité générale de ton bureau et réagit "
        "par petites touches pendant que tu travailles, joues et explores.",
    ),
    ("Ambient Reactions", "Réactions ambiantes"),
    (
        "AmbiSense uses broad, privacy-reduced activity signals rather than the "
        "content of what you type. Depending on what your desktop exposes, Mochi "
        "may respond with animations, behavior changes, or an occasional phrase.",
        "AmbiSense utilise des signaux d’activité généraux et respectueux de la vie "
        "privée, jamais le contenu de ce que tu tapes. Selon ce que ton bureau "
        "expose, Mochi peut répondre par des animations, des changements de "
        "comportement ou une petite phrase de temps en temps.",
    ),
    ("Typing and sustained typing activity", "La frappe au clavier, courte ou soutenue"),
    ("Coding and editor activity, including VS Code", "La programmation et les éditeurs, dont VS Code"),
    ("Terminal activity", "L’activité dans le terminal"),
    ("Music playback", "La lecture de musique"),
    ("YouTube and supported video activity", "YouTube et les vidéos prises en charge"),
    (
        "Idle/return periods, file browsing, and other supported desktop activity",
        "Les absences et les retours, la navigation dans les fichiers et d’autres "
        "activités prises en charge",
    ),
    ("Play With Mochi", "Jouer avec Mochi"),
    (
        "You do not have to interact with Mochi, but he does notice when you do.",
        "Pas besoin d’interagir avec Mochi, mais il remarque quand tu le fais.",
    ),
    (
        "Hover over Mochi — he may answer with a little heart.",
        "Survole Mochi — il peut te répondre avec un petit cœur.",
    ),
    (
        "Left-click — a tactile bounce or squish with a tiny chirp.",
        "Clic gauche — un rebond ou un écrasement avec un petit gazouillis.",
    ),
    ("Double-click — a heart emote.", "Double-clic — une émote cœur."),
    (
        "Drag — pick Mochi up and move him around the desktop.",
        "Glisser — attrape Mochi et déplace-le sur le bureau.",
    ),
    ("Right-click — open Mochi's user menu.", "Clic droit — ouvre le menu de Mochi."),
    ("Little Thoughts", "Petites pensées"),
    (
        "Mochi may occasionally show a short phrase connected to what is happening "
        "around the desktop. They are intentionally lightweight, paced out, and "
        "easy to ignore when you are busy.",
        "Mochi peut parfois afficher une courte phrase liée à ce qui se passe sur "
        "le bureau. Elles sont volontairement légères, espacées et faciles à "
        "ignorer quand tu as autre chose à faire.",
    ),
    ("Focus With Mochi", "Se concentrer avec Mochi"),
    (
        "Right-click Mochi to run a gentle focus/break session together. Focused "
        "minutes grow your bond; breaks stay pressure-free.",
        "Fais un clic droit sur Mochi pour lancer ensemble une douce séance de "
        "concentration et de pauses. Les minutes de concentration font grandir "
        "votre lien; les pauses restent sans pression.",
    ),
    ("You’re in Control", "C’est toi qui décides"),
    (
        "The right-click menu lets you sleep or wake Mochi, toggle Edge roam, use "
        "Stay put to stop autonomous wandering, and close Mochi. More granular "
        "AmbiSense controls for speech bubbles, ambient reactions, and quiet mode "
        "currently live in Mochi Lab, which is a developer/testing surface.",
        "Le menu du clic droit te permet d’endormir ou de réveiller Mochi, "
        "d’activer « Longer les bords », d’utiliser « Rester sur place » pour "
        "arrêter ses promenades, et de fermer Mochi. Les réglages plus fins "
        "d’AmbiSense (bulles, réactions ambiantes, mode silencieux) se trouvent "
        "pour l’instant dans le Mochi Lab, un espace pour les développeurs et les tests.",
    ),
    ("Try This", "Essaie ça"),
    ("A few easy ways to see Mochi react:", "Quelques façons simples de voir Mochi réagir :"),
    ("Open VS Code and type for a bit.", "Ouvre VS Code et tape un peu."),
    (
        "Focus a terminal and work there for a moment.",
        "Va dans un terminal et travailles-y un moment.",
    ),
    ("Play some music.", "Fais jouer de la musique."),
    ("Pick Mochi up and move him around.", "Attrape Mochi et déplace-le."),
    (
        "Leave him alone for a while and see what he decides to do.",
        "Laisse-le tranquille un moment et regarde ce qu’il décide de faire.",
    ),
    (
        "That’s enough reading. Go bother Mochi. 🌱",
        "Assez lu. Va embêter Mochi. 🌱",
    ),
    # Focus window
    ("Focus with Mochi 🌱", "Se concentrer avec Mochi 🌱"),
    ("WORK WITH MOCHI", "TRAVAILLER AVEC MOCHI"),
    (
        "A gentle focus timer. Your bond grows as you focus.",
        "Une minuterie de concentration tout en douceur. Votre lien grandit pendant que tu te concentres.",
    ),
    ("Focus", "Concentration"),
    ("Break", "Pause"),
    ("Rounds", "Tours"),
    ("Gentle encouragement", "Encouragements doux"),
    (
        "Focus time earns bond XP. Breaks are yours — Mochi does not grade them.",
        "Le temps de concentration rapporte de l’XP de lien. Les pauses sont à toi — Mochi ne les note pas.",
    ),
    ("Start focusing", "Commencer"),
    ("Focus {round} of {rounds}", "Concentration {round} sur {rounds}"),
    ("Break {round} of {rounds}", "Pause {round} sur {rounds}"),
    ("Complete", "Terminé"),
    ("{minutes} focused minutes together", "{minutes} minutes de concentration ensemble"),
    ("Pause", "Pause"),
    ("Resume", "Reprendre"),
    ("Done", "Terminé"),
    ("Stop session", "Arrêter la séance"),
    (
        "You can close this window. The timer keeps going with Mochi.",
        "Tu peux fermer cette fenêtre. La minuterie continue avec Mochi.",
    ),
    ("Rain sounds", "Bruit de pluie"),
    ("Rain volume", "Volume de la pluie"),
    # Emote Catalogue
    ("Mochi Emote Catalogue", "Catalogue d’émotes de Mochi"),
    ("MOCHI COLLECTION", "COLLECTION DE MOCHI"),
    ("Emote Catalogue", "Catalogue d’émotes"),
    (
        "Grow your bond with Mochi to reveal more little moods.",
        "Fais grandir ton lien avec Mochi pour découvrir d’autres petites humeurs.",
    ),
    ("Previous emote page", "Page d’émotes précédente"),
    ("Next emote page", "Page d’émotes suivante"),
    (
        "Ctrl + Alt + E · ←/→ pages · Esc to close",
        "Ctrl + Alt + E · ←/→ pages · Échap pour fermer",
    ),
    ("COMING SOON", "BIENTÔT"),
    ("UNLOCKED", "DÉBLOQUÉE"),
    ("BOND LV. {level}", "LIEN NIV. {level}"),
    ("A future little mood.", "Une future petite humeur."),
    ("A little mood Mochi has learned.", "Une petite humeur que Mochi a apprise."),
    ("Keep bonding to discover this mood.", "Continue de tisser votre lien pour découvrir cette humeur."),
    (
        "Bond Lv. {level} · all available emotes unlocked (developer) ✦",
        "Lien niv. {level} · toutes les émotes disponibles débloquées (développeur) ✦",
    ),
    (
        "Bond Lv. {level} · all current emotes unlocked ✦",
        "Lien niv. {level} · toutes les émotes actuelles débloquées ✦",
    ),
    (
        "Bond Lv. {level} · Next: {emote} at Lv. {target} · {remaining:,} XP to go",
        "Lien niv. {level} · Prochaine : {emote} au niv. {target} · encore {remaining:,} XP",
    ),
    ("COMMON", "COMMUNE"),
    ("UNCOMMON", "PEU COMMUNE"),
    ("RARE", "RARE"),
    ("EPIC", "ÉPIQUE"),
    ("LEGENDARY", "LÉGENDAIRE"),
    # Emote names
    ("Heart", "Cœur"),
    ("Bounce", "Rebond"),
    ("Squish", "Écrasement"),
    ("Wave", "Salut"),
    ("Coffee", "Café"),
    ("Side Eye", "Regard en coin"),
    ("Look Around", "Coup d’œil"),
    ("Table Flip", "Table renversée"),
    ("This Is Fine", "Tout va bien"),
    ("VS Code", "VS Code"),
    ("Dance", "Danse"),
    ("Mochi.exe", "Mochi.exe"),
    # Bond progress
    ("Bond XP", "XP de lien"),
    ("Bond Lv. {level}", "Lien niv. {level}"),
    ("Bond Level {level}", "Lien niveau {level}"),
    ("{xp}/{required} bond XP ({percent}%)", "{xp}/{required} XP de lien ({percent} %)"),
    ("bonding", "complicité"),
    ("sharing a snack", "on partage une collation"),
    ("✦  LEVEL UP!  ✦", "✦  NIVEAU SUPÉRIEUR!  ✦"),
    ("✦  NEW EMOTE UNLOCKED!  ✦", "✦  NOUVELLE ÉMOTE DÉBLOQUÉE!  ✦"),
    (
        "{rarity} · Bond Lv. {level} · now part of Mochi's idle moods",
        "{rarity} · Lien niv. {level} · fait maintenant partie des humeurs de Mochi",
    ),
    # Pocket
    ("Held 1 item", "1 objet gardé"),
    ("Held {count} items", "{count} objets gardés"),
    (" · removed the oldest 1 item", " · le plus ancien a été retiré"),
    (" · removed the oldest {count} items", " · les {count} plus anciens ont été retirés"),
    ("My paws are full", "J’ai les pattes pleines"),
    ("I couldn't hold that", "Je n’ai pas pu garder ça"),
    ("I can't hold that yet", "Je ne peux pas encore garder ça"),
    ("I couldn't update Pocket", "Je n’ai pas pu mettre à jour la Poche"),
    ("Open", "Ouvrir"),
    ("View", "Voir"),
    ("Dropped image · {received}", "Image déposée · {received}"),
    ("Text · {received}", "Texte · {received}"),
    ("Unavailable · {subtitle}", "Indisponible · {subtitle}"),
    ("Clear Pocket?", "Vider la Poche?"),
    (
        "Remove everything from Pocket? Original files on your computer will not be deleted.",
        "Tout retirer de la Poche? Les fichiers originaux sur ton ordinateur ne seront pas supprimés.",
    ),
    ("Cancel", "Annuler"),
    ("Clear All", "Tout vider"),
    ("Mochi Pocket", "Poche de Mochi"),
    ("Pocket", "Poche"),
    ("Remove everything from Pocket", "Tout retirer de la Poche"),
    ("The latest things Mochi is holding for you.", "Les dernières choses que Mochi garde pour toi."),
    (
        "Pocket is empty. Drag a file, link, image, or text onto Mochi.",
        "La Poche est vide. Glisse un fichier, un lien, une image ou du texte sur Mochi.",
    ),
    ("That item is no longer available.", "Cet objet n’est plus disponible."),
    ("Mochi couldn't open that item: {error}", "Mochi n’a pas pu ouvrir cet objet : {error}"),
    ("Mochi couldn't open that folder: {error}", "Mochi n’a pas pu ouvrir ce dossier : {error}"),
    ("Mochi couldn't remove that item.", "Mochi n’a pas pu retirer cet objet."),
    ("Mochi couldn't clear Pocket.", "Mochi n’a pas pu vider la Poche."),
    ("Open containing folder", "Ouvrir le dossier"),
    ("Remove from Pocket", "Retirer de la Poche"),
    # Update menu row (the updater window itself is a standalone package and stays English)
    ("Couldn’t check for updates.", "Impossible de rechercher les mises à jour."),
    (
        "Update check failed without additional details.",
        "La recherche de mises à jour a échoué sans plus de détails.",
    ),
)
