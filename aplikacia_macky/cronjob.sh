#!/bin/bash

# Definícia premenných pre cesty
backup_dir="/home/adam/Plocha/BP/BP/aplikacia_macky"  # Cesta k záložnému adresáru
media_adresar="/home/adam/Plocha/BP/BP/aplikacia_macky/media"  # Cesta k adresáru s médiami
media_zaloha_adresar="/home/adam/Plocha/BP/BP/aplikacia_macky/media_zaloha"
zaloha_sql_subor="/home/adam/Plocha/BP/BP/aplikacia_macky/app_macky_dump.sql"  # Cesta k súboru zálohy

# Začiatočný dátum, od ktorého sa počíta periodické spúšťanie
datum_zaciatok="2024-01-02"

# Aktuálny dátum
datum_aktualny=$(date '+%Y-%m-%d')

# Vypočítanie počtu dní od začiatočného dátumu
pocet_dni=$(( ( $(date -d "$datum_aktualny" '+%s') - $(date -d "$datum_zaciatok" '+%s') ) / 86400 ))

# Podmienka pre spúšťanie každý druhý deň
if [ $((pocet_dni % 2)) -eq 0 ]; then
  # Príkaz na zálohovanie databázy
  pg_dump -U postgres -h localhost -d app_macky -W > "$zaloha_sql_subor"

  # Odstránenie obsahu zalohovacieho adresára
  rm -rf "$media_zaloha_adresar"/*

  # Kopírovanie obsahu adresára media(s obrázkami) do zálohovacieho adresára
  cp -r "$media_adresar"/* "$media_zaloha_adresar"
fi

