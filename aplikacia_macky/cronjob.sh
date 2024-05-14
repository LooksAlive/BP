#!/bin/bash

# východiskový dátum s ktorým sa počíta
# POZNAMKA: ak chceme začať dnes periodicky, nastavíme o jeden den menší dátum: 1 mod 7 = 1, pozor 0 mod 7 = 0 (ak by bol datum_aktualny == datum_zaciatok, teda záloha by sa vykonala dnes)
# -------------------------------------
datum_zaciatok="2024-01-02"
# -------------------------------------


datum_aktualny=$(date '+%Y-%m-%d')
pocet_dni=$(( ( $(date -d "$datum_aktualny" '+%s') - $(date -d "$datum_zaciatok" '+%s') ) / 86400 ))

# 
if [ $((pocet_dni % 2)) -eq 0 ]; then
  pg_dump -U postgres -h localhost -d app_macky -W > "/home/adam/Plocha/BP/BP/app_macky_dump1.sql"
  rm -rf /home/adam/Plocha/BP/BP/aplikacia_macky/media1/*
  cp -r /home/adam/Plocha/BP/BP/aplikacia_macky/media/* /home/adam/Plocha/BP/BP/aplikacia_macky/media1
fi


# "/mnt/data/app_macky_dump.sql"ls

