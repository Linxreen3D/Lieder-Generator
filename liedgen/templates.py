"""Offline-Textbausteine (Fallback ohne Claude-API-Key).

Die Bausteine sind bewusst einfach – sie liefern sofort Suno-taugliche Entwürfe,
die der Viral-Score bewerten kann. Für veröffentlichungsreife Texte den
Claude-Backend nutzen (ANTHROPIC_API_KEY) und Texte immer selbst gegenlesen.
"""

BANK: dict[str, dict] = {
    "nordic_folk_pop": {
        "hooks": [
            ("Carry Me Home", ["Oh-oh, carry me home", "Over the water, over the stone",
                               "Oh-oh, carry me home", "Where the north wind sings alone"]),
            ("Northern Fire", ["Burn, burn, northern fire", "Lift my soul a little higher",
                               "Burn, burn, northern fire", "Hey! Hey! Northern fire"]),
            ("Raven Calls", ["Hear the raven call your name", "Through the frost and through the flame",
                             "Hear the raven call your name", "Oh-oh, nothing stays the same"]),
        ],
        "verse": ["Cold light falling on the bay", "Our fathers' boats have sailed away",
                  "I hear the drums beneath the ice", "Your voice is calling through the night",
                  "Pine and ash and silver sea", "The old gods whisper back to me",
                  "We lit the fire on the hill", "The winter wolves are standing still",
                  "Salt is drying on my skin", "The northern lights are pulling in"],
        "pre": ["And the storm is rising, rising", "Can you feel the ground divide",
                "Hold on, hold on to me", "Let the thunder set us free"],
        "bridge": ["Skål to the ones we lost", "Skål to the ones who stay",
                   "We will find you in the frost", "When the night turns into day"],
    },
    "balkan_ballade": {
        "hooks": [
            ("Ostani Još Noćas", ["Ostani još noćas, ljubavi", "Ne idi, srce moje, ne idi",
                                   "Ostani još noćas, ljubavi", "Bez tebe ne znam kako živi se"]),
            ("Rana Moja", ["Ti si rana moja, ti si lijek", "Volim te i mrzim te za vijek",
                           "Ti si rana moja, ti si lijek", "Rana moja, ti si moj grijeh"]),
            ("Majko", ["Majko, majko, vrati me kući", "Daleko sam, a srce se lomi",
                       "Majko, majko, vrati me kući", "Tamo gdje me niko ne zaboravi"]),
        ],
        "verse": ["Kafana prazna, čaša puna", "A ti si otišla bez riječi",
                  "Na stolu stoji tvoja slika", "Ni vino više ne liječi",
                  "U tuđem gradu kiša pada", "Moje ime niko ne zna",
                  "Sve što imam dao bih ti", "Samo da si opet tu"],
        "pre": ["A noć je duga, duga bez tebe", "Svaka suza zove te",
                "Reci mi, reci mi zašto"],
        "bridge": ["Ako me ikada voljela si", "Vrati se, vrati se sad"],
    },
    "deutschrap_street": {
        "hooks": [
            ("Kein Zurück", ["Kein Zurück, nur nach vorne (ja)", "Kopf hoch, auch wenn es kalt wird",
                             "Kein Zurück, nur nach vorne", "Wir hol'n uns alles, was bald wird"]),
            ("Nachtschicht", ["Nachtschicht, Blick auf die Stadt (ey)", "Jeder will was, keiner hat's",
                              "Nachtschicht, Blick auf die Stadt", "Ich bleib wach, bis ich es hab"]),
        ],
        "verse": ["Damals nur Beton, heute Blick übers Dach", "Mama hat geweint, ich hab' heimlich gelacht",
                  "Jeder Euro schwer, jeder Schritt war ein Kampf", "Freunde wurden Fremde, doch ich bleib, wie ich kam",
                  "Graue Blocks, kalter Wind, wir war'n Kinder der Nacht", "Haben nix gehabt, doch haben alles gemacht",
                  "Sie reden viel, doch sie kennen nicht den Weg", "Jeder Stein, den ich trag, ist ein Teil von dem Steg",
                  "Kein Plan B, nur der Hunger im Bauch", "Was sie Glück nennen, nenn' ich Arbeit und Rauch",
                  "Brüder an der Seite, wenn das Licht ausgeht", "Loyalität bleibt, auch wenn der Wind sich dreht"],
        "pre": [],
        "bridge": [],
    },
    "deutschrap_melodic": {
        "hooks": [
            ("3 Uhr Nachts", ["3 Uhr nachts und du bist nicht da", "Alles dreht sich, doch nichts ist klar",
                              "3 Uhr nachts und du bist nicht da", "Ich vermiss dich wie im letzten Jahr"]),
            ("Sommer auf dem Balkon", ["Sommer auf dem Balkon, nur du und ich", "Die Stadt ist laut, doch ich hör sie nicht",
                                       "Sommer auf dem Balkon, nur du und ich", "Bleib noch, bis die Sonne bricht"]),
        ],
        "verse": ["Späti-Licht und dein Lachen im Ohr", "Ich hab' dich gesucht und mich selbst verlor'n",
                  "S-Bahn leer, der Kopf ist voll", "Weiß nicht, ob ich gehen oder bleiben soll",
                  "Deine Jacke liegt noch bei mir", "Und jedes Lied erzählt von dir",
                  "Wir waren jung und die Nächte lang", "Weißt du noch, wie alles begann"],
        "pre": ["Und ich frag mich, wo du bist", "Ob du mich auch so vermisst"],
        "bridge": [],
    },
    "phonk": {
        "hooks": [
            ("Vai Vai Vai", ["Vai, vai, vai (ah!)", "Vai, vai, vai", "Vai, vai, vai (ah!)", "Vai, vai, vai"]),
            ("Noite Escura", ["Noite escura (hey!)", "Noite escura", "Noite escura (hey!)", "Noite escura"]),
        ],
        "verse": [], "pre": [], "bridge": [],
    },
    "afro_house": {
        "hooks": [
            ("Dance Into The Sun", ["Dance into the sun (oh-ee-oh)", "Now we are one",
                                    "Dance into the sun (oh-ee-oh)", "Our hearts beat as one"]),
            ("Higher Ground", ["Take me to the higher ground", "Feel the drums, feel the sound",
                               "Take me to the higher ground", "Never coming down"]),
        ],
        "verse": ["The ocean calls my name tonight", "Your hands are glowing in the light",
                  "We move together, slow and free", "The rhythm living inside of me",
                  "Barefoot on the burning sand", "The world is spinning in your hand"],
        "pre": [], "bridge": [],
    },
    "schlager_party": {
        "hooks": [
            ("Malle Ist Kein Ort", ["Malle ist kein Ort, Malle ist ein Gefühl", "Hände hoch, ab heut wird gespielt",
                                    "Malle ist kein Ort, Malle ist ein Gefühl", "Ole, ole, wir sind am Ziel"]),
            ("Eins Zwei Prost", ["Eins, zwei, Prost – und alle singen mit", "Heut Nacht kommt keiner mehr nach Haus zurück",
                                 "Eins, zwei, Prost – und alle singen mit", "Hey! Hey! Noch einen Schritt"]),
        ],
        "verse": ["Montag noch im Büro, Kaffee kalt", "Dienstag schon am Strand, ich werd nicht alt",
                  "Der Chef ruft an, ich geh nicht ran", "Weil ich heut nur noch feiern kann",
                  "Die Sonne lacht, das Bier ist kalt", "Der ganze Laden singt so laut es schallt"],
        "pre": ["Und dann geht's los, und dann geht's los", "Jetzt alle zusammen, ganz famos"],
        "bridge": [],
    },
    "lofi_chill": {
        "hooks": [("Rain On The Window", []), ("Late Shift", []), ("Sunday Morning Tape", [])],
        "verse": [], "pre": [], "bridge": [],
    },
}
