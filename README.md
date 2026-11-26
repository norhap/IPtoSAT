# IPtoSAT
ENIGMA2 PLUGIN IPtoSAT

## Carátulas VOD con XtraEvent

Instale las versiones compatibles de IPToSAT y XtraEvent y reinicie Enigma2.
En IPToSAT, abra «Marcar bouquets de películas VOD» y marque con OK solo las
categorías que contienen películas. Salga y actualice los bouquets para guardar
la asociación entre cada servicio y el `tvg-logo` de la lista del proveedor.
Las marcas son independientes para cada suscripción. Después, en la
configuración de XtraEvent, active «Carátulas VOD de IPToSAT» y configure su
ubicación de almacenamiento. La skin debe usar `xtraPoster` con
`session.Event_Now` en la InfoBar.

La reproducción sigue usando la referencia existente. La imagen se descarga
en segundo plano desde la dirección proporcionada por el proveedor y se guarda
en la carpeta de XtraEvent. Si una entrada no trae imagen válida, no se muestra
una carátula alternativa. Tras cambiar las categorías marcadas, regenere los
bouquets; sin el `tvg-logo` del proveedor no se realiza ninguna búsqueda por
título. Las direcciones con redirección no se admiten en esta primera versión.
Para limitar el uso de memoria, solo se descarga una carátula VOD a la vez y
se rechazan imágenes de más de 5 MiB o 4 millones de píxeles.

El índice `/etc/enigma2/iptosat_vod_posters.json` contiene las direcciones de
las imágenes, que podrían incluir datos privados del proveedor: no lo comparta.
Si el mismo servicio aparece también en un bouquet no marcado, se identifica
por su dirección de reproducción y utilizará igualmente su carátula.

## Actualización del catálogo de listas

El botón amarillo descarga e indexa las listas de Jungle y ChannelLists en
segundo plano, mostrando las fases en pantalla. Si la actualización falla, se
mantiene el catálogo anterior. La instalación de una lista sigue siendo una
acción independiente.

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
