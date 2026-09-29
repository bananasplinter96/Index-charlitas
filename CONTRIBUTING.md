# Guía de Contribución 🤝

¡Gracias por tu interés en aportar a la **Index Knowledge Base**! Para garantizar la coherencia y calidad de la documentación, requerimos seguir este protocolo estricto.

## 📋 Reglas Generales

1. **Enlaces activos**: Verifica previamente que la URL responda correctamente (código HTTP 200).
2. **Sin duplicados**: Busca en [`/docs/`](./docs) antes de proponer un nuevo enlace.
3. **Clasificación adecuada**:
   - `docs/desarrollo.md`: Programación, frameworks, librerías, APIs y repositorios.
   - `docs/servidores.md`: Docker, Kubernetes, Linux, Cloud, VPS, bases de datos y redes.
   - `docs/qa_testing.md`: Testing, frameworks de pruebas, QA, certificaciones y ciberseguridad.
   - `docs/utilidades.md`: Herramientas online, generadores, conversores y productividad.

## 📐 Formato Estricto de Filas en Tablas

Cada aporte debe respetar el formato Markdown de 3 columnas:

```markdown
| Tema/Nombre | Descripción | Enlace |
| :--- | :--- | :--- |
| Nombre de la herramienta | Breve descripción de qué hace o por qué es útil | [https://ejemplo.com](https://ejemplo.com) |
```

### Especificaciones:
- **Tema/Nombre**: Título conciso del recurso o proyecto.
- **Descripción**: Resumen claro en 1 o 2 oraciones. No dejar en blanco ni repetir el nombre.
- **Enlace**: Siempre en formato markdown `[URL](URL)`.

## 🔄 Flujo de Trabajo (Git / Pull Requests)

1. Haz un Fork de este repositorio.
2. Crea una rama descriptiva:
   ```bash
   git checkout -b feature/recurso-nuevo
   ```
3. Añade la fila correspondiente en el archivo de categoría en `docs/`.
4. Haz commit respetando Conventional Commits:
   ```bash
   git commit -m "docs: agregar recurso de testing en qa_testing.md"
   ```
5. Abre un Pull Request describiendo tu aporte.
