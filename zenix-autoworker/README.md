# Zenix AutoWorker v1.1

## Lo que funciona
- Panel real en https://josenunezapps.github.io/zenix-autoworker/
- GitHub Actions lee issues publicos de GitHub y los registra como candidatos, no como empleos confirmados.
- Motor Python ejecuta una limpieza de CSV de prueba, genera un reporte comprobado y guarda entregables en Artifacts.
- Programacion con IA para un issue de GitHub: requiere un proveedor OpenRouter que autorices con tu propia clave. Genera archivos en entorno aislado y pasa comprobacion de sintaxis; no se aplican PRs a terceros.
- Nunca envia candidaturas, mensajes, PRs ni entregables a clientes. Nunca cobra automaticamente.

## Probar con GitHub, sin instalar
Abrir https://github.com/josenunezapps/josenunezapps.github.io/actions/workflows/zenix-autoworker.yml y seleccionar Run workflow. Sin parametros se buscan issues y se hace una tarea CSV.
Para intentar crear una solucion por IA, ingresar un enlace completo a un issue en el campo issue_url.

## Configuracion de IA
1. Ir a GitHub repositorio -> Settings -> Secrets and variables -> Actions.
2. Crear un Repository secret llamado OPENROUTER_API_KEY, con una clave propia de https://openrouter.ai/ . No compartir la clave por chat ni subirla como archivo.
3. Opcionalmente crear la variable AUTO_WORKER_MODEL para seleccionar modelo. Por defecto intenta openrouter/free; disponibilidad y limites pueden cambiar.
4. Ejecutar el workflow y descargar el artifact zenix-autoworker-deliverables desde el resultado.
5. Revisar manualmente el reporte y archivos antes de contactar al dueño del issue.

Los proveedores de IA pueden cobrar segun modelo. GitHub Models cerro en julio de 2026.

## Restricciones
- Repo publico: no subir codigo de clientes, contraseñas ni datos privados.
- El motor no verifica pagos y puede encontrar issues con falsas recompensas.
- Las validaciones actuales revisan sintaxis basica Python/JSON, NO garantizan que una correccion funcione.
- Si Docker no esta disponible, la verificacion se marca como incompleta.
- No hay postulacion ni entrega automatica: estan bloqueadas por diseño.
- GitHub Actions se utiliza aqui solo para pruebas de desarrollo bajo demanda, no como un servicio comercial permanente. El modo continuo debera ejecutarse en infraestructura apta para ello.

## Archivos
engine/agent.py: buscador y ejecutor real.
data/latest.json: resultados de las ejecuciones.
output/: artefactos para revision; no se guardan en el repositorio.
.github/workflows/zenix-autoworker.yml: trabajo programado en la raiz del repositorio.


## Actualización 1.2 — búsqueda con recompensas y controles de aprobación

Se integraron dos mercados reales, de **consulta solamente**:

1. Algora: obtiene bounties con importe publicado desde la API pública, verifica que haya una URL de issue GitHub y guarda la fuente. No garantiza que el dinero pueda cobrarse ni que el anuncio siga abierto.
2. BountyBoard: consulta anuncios públicos y descarta automáticamente los que NO autorizan agentes de IA, no sean de desarrollo, o no tengan cupos conocidos. No genera bids ni reclamaciones.

Resultados publicados en:
- `data/bounties.json`: Algora, estado actual, precio anunciado, pago no verificado.
- `data/bountyboard.json`: BountyBoard y razones de exclusión.
- `data/reviews.json`: decisiones humanas públicas; **no poner datos privados de clientes**.

### Cómo probar las aprobaciones (solo QA de desarrollo)

1. Entra en el workflow **Zenix AutoWorker - Approval QA** de GitHub Actions.
2. Acción `prepare`, URL `https://github.com/josenunezapps/josenunezapps.github.io/issues/1` y título de la tarea. Esto prepara una propuesta y un expediente público.
3. `approve_apply`: el usuario dueño del repositorio autoriza que se prepare una postulación. **No se envía nada**.
4. `mark_applied`: solo después de que una persona haya hecho realmente la postulación, registrar evidencia pública.
5. `ready_delivery`: exige el SHA256 del artefacto revisado, luego `approve_delivery`.
6. `mark_delivered`: solo después de que una persona haya entregado realmente los archivos, registrar constancia pública.

El workflow valida la identidad autenticada de GitHub y guarda la auditoría. Si intentás saltar una etapa, rechaza la operación.

### Para pasar de las pruebas al trabajo remunerado

- Verificar un anuncio elegible, que acepte IA, que tenga recompensa y que pueda pagarse a una cuenta de Argentina.
- Obtener aceptación del trabajo conforme a las normas de cada plataforma.
- Revisar la calidad técnica de la solución, sus licencias y las pruebas de funcionamiento.
- Implementar un backend seguro y un trabajador aislado en infraestructura adecuada (GitHub Pages es estático).
- Integrar postulaciones y entregas **solamente** en plataformas autorizadas, tras una decisión humana explícita.

GitHub Actions se utiliza aquí **para desarrollo y pruebas**, no como infraestructura para ejecutar un negocio automático permanente. No se promete ingreso alguno.
