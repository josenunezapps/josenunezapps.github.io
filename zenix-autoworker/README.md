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
