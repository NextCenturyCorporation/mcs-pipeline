#!/bin/bash
# This script should be run via source in most cases. I.E. source load_ini.sh my-config.ini
# 
# Read locations file and put in variables.  Variables are simply the concatentation of section and then variable with
# an underscore between.
#
# I.E. if the file is:
# [MCS]
# var1=test
#
# there should be a variable called MCS_var1 after this is executed.
#
# See https://serverfault.com/questions/345665/how-to-parse-and-convert-ini-file-into-bash-array-variables

while IFS='= ' read var val
do
    if [[ $var == \;* ]]
    then
        continue
    fi
    if [[ $var == \#* ]]
    then
        continue
    fi
    if [[ $var == \[*] ]]
    then
        section=${var//[}
        section=${section//]}
    elif [[ $val ]]
    then
        declare "${section}_${var}=$val"
    fi
done < $1
