# IPtoSAT
ENIGMA2 PLUGIN IPtoSAT

## EPG IPTV y DVB

Los canales TDT y autonómicos identificados en la lista IPTV pueden utilizar
referencias EPG IPTV propias cuando no se ha seleccionado una referencia DVB.
Así la guía IPTV no sustituye la EPG DVB de la TDT, que puede variar según la
zona. Los canales de Movistar disponibles por satélite deben mantener su
referencia DVB y no añadirse al mapa de EPG IPTV. Cuando el nombre IPTV de
Movistar coincide con una entrada de `iptosatreferences`, se reutiliza su clave
EPG DVB incluso para variantes SD, siempre que el nombre del servicio DVB
coincida; también se aplica a otros canales con referencia de satélite. La
guía depende de la recepción DVB.

Las referencias IPTV adicionales cubren canales de ES1 y Rakuten España,
incluidas variantes diferenciadas de Iberalia, OneToro y Pop Up 1 y 2. Un
nombre sin número como `M+ PopUP` no permite distinguir los dos últimos y se
deja sin asignación en lugar de escoger una guía potencialmente incorrecta.

Tras actualizar el plugin y el mapa de EPGImport instalado, hay que regenerar
los bouquets IPTV para aplicar las referencias nuevas.

## Actualización automática y apagado

Si el receptor despierta por el temporizador de IPToSAT y está configurado
para volver a deep standby, espera a que termine la importación EPG (hasta
dos horas). El apagado se cancela si se usa el mando, cambia el estado de
standby, se está usando timeshift o hay actividad que impida apagar. Un búfer
automático de timeshift que no se esté usando no impide el apagado por sí solo.
Los motivos se registran en
`/tmp/IPToSAT.log`.
