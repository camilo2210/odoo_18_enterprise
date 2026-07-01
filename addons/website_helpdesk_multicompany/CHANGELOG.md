# Website Helpdesk Multi-Company

## Descripción
Publica en `/helpdesk` los equipos de soporte de todas las compañías de la base
de datos. El acceso a un equipo concreto se restringe a las compañías a las que
pertenece el usuario (`res.users.company_ids`); si el equipo es de otra compañía
se muestra una página de acceso restringido en lugar de un error.
 
## Changelog / Registro de Cambios

### [18.0.1.0.0] - 2026-07-01
#### Añadido
- Lista en `/helpdesk` con los equipos de todas las compañías (vía `sudo`,
  saltando la ir.rule "Team: multi-company").
- Restricción de acceso por compañía: solo se entra a equipos cuya `company_id`
  esté en `res.users.company_ids`. Para esos equipos se amplían las
  `allowed_company_ids` del contexto y así la ir.rule deja leer el equipo y sus
  campos SEO sin usar `sudo` en la plantilla (evita el `AccessError` al renderizar
  `website.layout`).
- Página `team_access_denied` cuando el equipo pertenece a otra compañía.

## Autores
- PROGSUM

## Mantenedores
- PROGSUM

