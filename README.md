# NOESIS Shorts Pipeline

Il flusso di PierVillain parte da un video lungo e produce Shorts verticali e una copertina per il video originale. Il montaggio usa Python e FFmpeg. La selezione delle clip e la generazione della copertina si fanno in ChatGPT.

## Preparazione

1. Parti da un MP4 locale e dalla sua trascrizione con timecode. Chiedi a ChatGPT di proporre quattro estratti da 20–35 secondi che si capiscano da soli. Rivedi i tagli sul video, poi inserisci in `inputs/clips.json` i secondi di inizio e fine e un nome univoco per ogni clip.
2. Genera la copertina del video lungo con ChatGPT Image usando [il prompt](cover-prompt.md). Salva l'immagine in `inputs/cover.png`.
3. Per i sottotitoli, aggiungi a una clip il campo `captions` con il percorso di un file SRT relativo a `clips.json`. I timecode dell'SRT partono dall'inizio della clip. Se il soggetto è decentrato, imposta `focus` fra 0 (sinistra) e 1 (destra). Il valore predefinito è 0,5.

Esempio di `clips.json` con una clip:

```json
[
  {"name": "dal-contatto-alla-call", "start": 12.3, "end": 41.1}
]
```

## Montaggio

Occorrono Python 3.10+ e `ffmpeg` e `ffprobe` nel PATH. Per i sottotitoli serve una build di FFmpeg con libass.

```sh
python render.py inputs/video.mp4 inputs/clips.json inputs/cover.png exports/episodio
```

Il comando produce un MP4 1080 × 1920 a 30 fps per clip e `cover.jpg` a 1280 × 720 per il video lungo. FFmpeg verifica la decodifica prima di consegnare gli output. Scegli una cartella di destinazione nuova per ogni esportazione. Apri gli MP4 per rivedere tagli, inquadratura e sottotitoli prima di caricarli su YouTube o TryPost.

Tieni i video, le immagini dell'episodio e le trascrizioni in `inputs/` e i file esportati in `exports/`. Entrambe le cartelle sono escluse da Git.
