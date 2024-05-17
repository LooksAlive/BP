#!/bin/bash

# Definícia premenných pre cesty
backup_dir="/home/adam/Plocha/BP/BP"  # Cesta k záložnému adresáru
media_dir="/home/adam/Plocha/BP/BP/aplikacia_macky/media"  # Cesta k adresáru s médiami
backup_file="$backup_dir/app_macky_dump1.sql"  # Cesta k súboru zálohy

# Začiatočný dátum, od ktorého sa počíta periodické spúšťanie
datum_zaciatok="2024-01-01"

# Aktuálny dátum
datum_aktualny=$(date '+%Y-%m-%d')

# Vypočítanie počtu dní od začiatočného dátumu
pocet_dni=$(( ( $(date -d "$datum_aktualny" '+%s') - $(date -d "$datum_zaciatok" '+%s') ) / 86400 ))

# Podmienka pre spúšťanie každý druhý deň
if [ $((pocet_dni % 2)) -eq 0 ]; then
  # Príkaz na zálohovanie databázy
  pg_dump -U postgres -h localhost -d app_macky -W > "$backup_file"

  # Odstránenie obsahu priečinka media1
  rm -rf "$backup_dir/aplikacia_macky/media1"/*

  # Kopírovanie obsahu priečinka media do media1
  cp -r "$media_dir"/* "$backup_dir/aplikacia_macky/media1"
fi

