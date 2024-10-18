#!/bin/bash
echo "testing: pdftitle -p paran2010.pdf -a max2 -t"
title=$(pdftitle -p paran2010.pdf -a max2 -t)
echo "\"$title\""
if [ $? -eq 0 ]; then
  if [ ! "$title" = "Settlement Remains From The Bronze And Iron Ages At Horbat Menorim (El-Manara), Lower Galilee" ]; then
    exit 1
  fi
  exit 0
else
  exit 1
fi
