desarrollo de frontned:


la plantilla actual esta bien como base, pero falta realizar mejoras, para empezar, definire las opciones que deben estar en la parte lateral izquierda, debe haber una seccion usuarios, donde se pueda hacer mantenimiento de usuarios, como inactivar, crear nuevos usuarios, cambiar el rol, cambiar la contraseña de los usuarios , esto solo lo puede hacer el administrador, luego, tambien debe haber una seccion para editar los bancos, las cuentas bancarias y su alias, las sucursales, los vendedores, luego otra seccion del arbol de tipificaciones donde se muestre visualmente la jerarquia conforme creo tipificaciones.

luego debe haber una seccion de configuracion de divisas, aca podre indicar el tipo de cambio que quiero que se active para los movimientos, esto para la cuenta dolares, porque te menciono esto?, porque a veces hacemos transferencias entre cuentas propias, de dolares a soles, en dolares se va a mostrar el monto de 60$, y la que recibe, supongamos, se muestra como 180 soles, el cuadre debe considerar estas variables,

tambien debe haber un boton para ingresar registros bancarios manualmente, es decir , sin necesidad de importarlo masivamente, ahora, he probado la funcionalidad para subir tipificaciones masivas y me salen varios errores: 

 
 POST http://localhost:8000/api/v1/imports/csv 422 (Unprocessable Content)
request	@	src/client/api.ts:13
importCsv	@	src/client/api.ts:37
mutationFn	@	src/pages.tsx:751
await in execute		
onClick	@	src/pages.tsx:804



adicionalmente ingresa registros de prueba a la base de datos para poder testear el funcionamiento 