-- ==========================================
-- usuarios.0005
-- ==========================================

BEGIN;
--
-- Add field es_becado to usuario
--
CREATE TABLE "new__core_usuario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "es_becado" bool NOT NULL, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "nombre" varchar(120) NOT NULL, "apellido" varchar(120) NOT NULL, "celular" varchar(30) NOT NULL UNIQUE, "es_profe" bool NOT NULL, "foto_perfil" varchar(100) NULL, "mp_access_token" varchar(500) NULL, "mp_public_key" varchar(500) NULL, "dni" varchar(15) NOT NULL, "fecha_nacimiento" date NULL, "domicilio" varchar(255) NOT NULL, "localidad" varchar(150) NOT NULL, "fecha_ingreso_real" date NULL, "alergias" text NOT NULL, "condiciones_medicas" text NOT NULL, "contacto_emergencia_nombre" varchar(120) NOT NULL, "contacto_emergencia_telefono" varchar(50) NOT NULL, "apto_medico" varchar(100) NULL, "uuid_carnet" char(32) NOT NULL UNIQUE, "fecha_vencimiento_cuota" date NULL, "rol_acceso_total" bool NOT NULL, "rol_gestion_alumnos" bool NOT NULL, "rol_gestion_sedes" bool NOT NULL, "rol_gestion_tienda" bool NOT NULL, "rol_gestion_tesoreria" bool NOT NULL, "rol_gestion_academia" bool NOT NULL, "autorizacion_tesoreria_activa" bool NOT NULL, "sede_id" bigint NULL REFERENCES "core_sede" ("id") DEFERRABLE INITIALLY DEFERRED, "grado_id" bigint NULL REFERENCES "core_grado" ("id") DEFERRABLE INITIALLY DEFERRED, "clases_disponibles" integer unsigned NOT NULL CHECK ("clases_disponibles" >= 0), "contacto_emergencia_direccion" varchar(200) NOT NULL, "fecha_prorroga" date NULL, "qr_base64_cache" text NULL, "tesorero_autorizado_id" bigint NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_usuario" ("id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado") SELECT "id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", 0 FROM "core_usuario";
DROP TABLE "core_usuario";
ALTER TABLE "new__core_usuario" RENAME TO "core_usuario";
CREATE INDEX "core_usuario_sede_id_2f29ed16" ON "core_usuario" ("sede_id");
CREATE INDEX "core_usuario_grado_id_474a31a3" ON "core_usuario" ("grado_id");
CREATE INDEX "core_usuario_tesorero_autorizado_id_c5e10368" ON "core_usuario" ("tesorero_autorizado_id");
--
-- Add field motivo_beca to usuario
--
CREATE TABLE "new__core_usuario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "nombre" varchar(120) NOT NULL, "apellido" varchar(120) NOT NULL, "celular" varchar(30) NOT NULL UNIQUE, "es_profe" bool NOT NULL, "foto_perfil" varchar(100) NULL, "mp_access_token" varchar(500) NULL, "mp_public_key" varchar(500) NULL, "dni" varchar(15) NOT NULL, "fecha_nacimiento" date NULL, "domicilio" varchar(255) NOT NULL, "localidad" varchar(150) NOT NULL, "fecha_ingreso_real" date NULL, "alergias" text NOT NULL, "condiciones_medicas" text NOT NULL, "contacto_emergencia_nombre" varchar(120) NOT NULL, "contacto_emergencia_telefono" varchar(50) NOT NULL, "apto_medico" varchar(100) NULL, "uuid_carnet" char(32) NOT NULL UNIQUE, "fecha_vencimiento_cuota" date NULL, "rol_acceso_total" bool NOT NULL, "rol_gestion_alumnos" bool NOT NULL, "rol_gestion_sedes" bool NOT NULL, "rol_gestion_tienda" bool NOT NULL, "rol_gestion_tesoreria" bool NOT NULL, "rol_gestion_academia" bool NOT NULL, "autorizacion_tesoreria_activa" bool NOT NULL, "sede_id" bigint NULL REFERENCES "core_sede" ("id") DEFERRABLE INITIALLY DEFERRED, "grado_id" bigint NULL REFERENCES "core_grado" ("id") DEFERRABLE INITIALLY DEFERRED, "clases_disponibles" integer unsigned NOT NULL CHECK ("clases_disponibles" >= 0), "contacto_emergencia_direccion" varchar(200) NOT NULL, "fecha_prorroga" date NULL, "qr_base64_cache" text NULL, "es_becado" bool NOT NULL, "motivo_beca" varchar(255) NOT NULL, "tesorero_autorizado_id" bigint NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_usuario" ("id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", "motivo_beca") SELECT "id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", '' FROM "core_usuario";
DROP TABLE "core_usuario";
ALTER TABLE "new__core_usuario" RENAME TO "core_usuario";
CREATE INDEX "core_usuario_sede_id_2f29ed16" ON "core_usuario" ("sede_id");
CREATE INDEX "core_usuario_grado_id_474a31a3" ON "core_usuario" ("grado_id");
CREATE INDEX "core_usuario_tesorero_autorizado_id_c5e10368" ON "core_usuario" ("tesorero_autorizado_id");
COMMIT;


-- ==========================================
-- usuarios.0006
-- ==========================================

BEGIN;
--
-- Add field dia_corte_cuota to usuario
--
CREATE TABLE "new__core_usuario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "dia_corte_cuota" smallint unsigned NOT NULL CHECK ("dia_corte_cuota" >= 0), "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "nombre" varchar(120) NOT NULL, "apellido" varchar(120) NOT NULL, "celular" varchar(30) NOT NULL UNIQUE, "es_profe" bool NOT NULL, "foto_perfil" varchar(100) NULL, "mp_access_token" varchar(500) NULL, "mp_public_key" varchar(500) NULL, "dni" varchar(15) NOT NULL, "fecha_nacimiento" date NULL, "domicilio" varchar(255) NOT NULL, "localidad" varchar(150) NOT NULL, "fecha_ingreso_real" date NULL, "alergias" text NOT NULL, "condiciones_medicas" text NOT NULL, "contacto_emergencia_nombre" varchar(120) NOT NULL, "contacto_emergencia_telefono" varchar(50) NOT NULL, "apto_medico" varchar(100) NULL, "uuid_carnet" char(32) NOT NULL UNIQUE, "fecha_vencimiento_cuota" date NULL, "rol_acceso_total" bool NOT NULL, "rol_gestion_alumnos" bool NOT NULL, "rol_gestion_sedes" bool NOT NULL, "rol_gestion_tienda" bool NOT NULL, "rol_gestion_tesoreria" bool NOT NULL, "rol_gestion_academia" bool NOT NULL, "autorizacion_tesoreria_activa" bool NOT NULL, "sede_id" bigint NULL REFERENCES "core_sede" ("id") DEFERRABLE INITIALLY DEFERRED, "grado_id" bigint NULL REFERENCES "core_grado" ("id") DEFERRABLE INITIALLY DEFERRED, "clases_disponibles" integer unsigned NOT NULL CHECK ("clases_disponibles" >= 0), "contacto_emergencia_direccion" varchar(200) NOT NULL, "fecha_prorroga" date NULL, "qr_base64_cache" text NULL, "es_becado" bool NOT NULL, "motivo_beca" varchar(255) NOT NULL, "tesorero_autorizado_id" bigint NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_usuario" ("id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", "motivo_beca", "dia_corte_cuota") SELECT "id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", "motivo_beca", 0 FROM "core_usuario";
DROP TABLE "core_usuario";
ALTER TABLE "new__core_usuario" RENAME TO "core_usuario";
CREATE INDEX "core_usuario_sede_id_2f29ed16" ON "core_usuario" ("sede_id");
CREATE INDEX "core_usuario_grado_id_474a31a3" ON "core_usuario" ("grado_id");
CREATE INDEX "core_usuario_tesorero_autorizado_id_c5e10368" ON "core_usuario" ("tesorero_autorizado_id");
--
-- Alter field fecha_prorroga on usuario
--
-- (no-op)
COMMIT;


-- ==========================================
-- usuarios.0007
-- ==========================================

BEGIN;
--
-- Add field ultima_prorroga_solicitada to usuario
--
ALTER TABLE "core_usuario" ADD COLUMN "ultima_prorroga_solicitada" date NULL;
COMMIT;


-- ==========================================
-- usuarios.0008
-- ==========================================

BEGIN;
--
-- Add field nivel_acceso to usuario
--
CREATE TABLE "new__core_usuario" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nivel_acceso" varchar(20) NOT NULL, "password" varchar(128) NOT NULL, "last_login" datetime NULL, "is_superuser" bool NOT NULL, "username" varchar(150) NOT NULL UNIQUE, "email" varchar(254) NOT NULL, "is_staff" bool NOT NULL, "is_active" bool NOT NULL, "date_joined" datetime NOT NULL, "nombre" varchar(120) NOT NULL, "apellido" varchar(120) NOT NULL, "celular" varchar(30) NOT NULL UNIQUE, "es_profe" bool NOT NULL, "foto_perfil" varchar(100) NULL, "mp_access_token" varchar(500) NULL, "mp_public_key" varchar(500) NULL, "dni" varchar(15) NOT NULL, "fecha_nacimiento" date NULL, "domicilio" varchar(255) NOT NULL, "localidad" varchar(150) NOT NULL, "fecha_ingreso_real" date NULL, "alergias" text NOT NULL, "condiciones_medicas" text NOT NULL, "contacto_emergencia_nombre" varchar(120) NOT NULL, "contacto_emergencia_telefono" varchar(50) NOT NULL, "apto_medico" varchar(100) NULL, "uuid_carnet" char(32) NOT NULL UNIQUE, "fecha_vencimiento_cuota" date NULL, "rol_acceso_total" bool NOT NULL, "rol_gestion_alumnos" bool NOT NULL, "rol_gestion_sedes" bool NOT NULL, "rol_gestion_tienda" bool NOT NULL, "rol_gestion_tesoreria" bool NOT NULL, "rol_gestion_academia" bool NOT NULL, "autorizacion_tesoreria_activa" bool NOT NULL, "sede_id" bigint NULL REFERENCES "core_sede" ("id") DEFERRABLE INITIALLY DEFERRED, "grado_id" bigint NULL REFERENCES "core_grado" ("id") DEFERRABLE INITIALLY DEFERRED, "clases_disponibles" integer unsigned NOT NULL CHECK ("clases_disponibles" >= 0), "contacto_emergencia_direccion" varchar(200) NOT NULL, "fecha_prorroga" date NULL, "qr_base64_cache" text NULL, "es_becado" bool NOT NULL, "motivo_beca" varchar(255) NOT NULL, "dia_corte_cuota" smallint unsigned NOT NULL CHECK ("dia_corte_cuota" >= 0), "ultima_prorroga_solicitada" date NULL, "tesorero_autorizado_id" bigint NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_usuario" ("id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", "motivo_beca", "dia_corte_cuota", "ultima_prorroga_solicitada", "nivel_acceso") SELECT "id", "password", "last_login", "is_superuser", "username", "email", "is_staff", "is_active", "date_joined", "nombre", "apellido", "celular", "es_profe", "foto_perfil", "mp_access_token", "mp_public_key", "dni", "fecha_nacimiento", "domicilio", "localidad", "fecha_ingreso_real", "alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico", "uuid_carnet", "fecha_vencimiento_cuota", "rol_acceso_total", "rol_gestion_alumnos", "rol_gestion_sedes", "rol_gestion_tienda", "rol_gestion_tesoreria", "rol_gestion_academia", "autorizacion_tesoreria_activa", "sede_id", "tesorero_autorizado_id", "grado_id", "clases_disponibles", "contacto_emergencia_direccion", "fecha_prorroga", "qr_base64_cache", "es_becado", "motivo_beca", "dia_corte_cuota", "ultima_prorroga_solicitada", 'alumno' FROM "core_usuario";
DROP TABLE "core_usuario";
ALTER TABLE "new__core_usuario" RENAME TO "core_usuario";
CREATE INDEX "core_usuario_sede_id_2f29ed16" ON "core_usuario" ("sede_id");
CREATE INDEX "core_usuario_grado_id_474a31a3" ON "core_usuario" ("grado_id");
CREATE INDEX "core_usuario_tesorero_autorizado_id_c5e10368" ON "core_usuario" ("tesorero_autorizado_id");
COMMIT;


-- ==========================================
-- usuarios.0009
-- ==========================================

BEGIN;
--
-- Add field qr_image to usuario
--
ALTER TABLE "core_usuario" ADD COLUMN "qr_image" varchar(100) NULL;
--
-- Alter field qr_base64_cache on usuario
--
-- (no-op)
COMMIT;


-- ==========================================
-- ventas.0002
-- ==========================================

BEGIN;
--
-- Create model Descuento
--
CREATE TABLE "core_descuento" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nombre" varchar(150) NOT NULL, "descripcion" text NOT NULL, "tipo" varchar(20) NOT NULL, "valor" decimal NOT NULL, "codigo" varchar(50) NOT NULL, "activo" bool NOT NULL, "usos_maximos" integer unsigned NULL CHECK ("usos_maximos" >= 0), "usos_actuales" integer unsigned NOT NULL CHECK ("usos_actuales" >= 0), "fecha_vencimiento" date NULL, "aplicable_a" varchar(20) NOT NULL);
--
-- Add field monto_descuento to pago
--
CREATE TABLE "new__core_pago" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "monto" decimal NOT NULL, "monto_comision_profesor" decimal NOT NULL, "monto_utilidad_asociacion" decimal NOT NULL, "motivo_rechazo" text NULL, "fecha_pago_real" date NULL, "tipo" varchar(20) NOT NULL, "cantidad_clases" integer NULL, "metodo" varchar(20) NOT NULL, "comprobante" varchar(100) NULL, "estado" varchar(20) NOT NULL, "mercado_pago_id" varchar(255) NULL, "mercado_pago_status" varchar(50) NULL, "fecha_registro" datetime NOT NULL, "actividad_id" bigint NULL REFERENCES "core_actividad" ("id") DEFERRABLE INITIALLY DEFERRED, "alumno_id" bigint NOT NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED, "clase_programada_id" bigint NULL REFERENCES "core_cronograma" ("id") DEFERRABLE INITIALLY DEFERRED, "monto_descuento" decimal NOT NULL);
INSERT INTO "new__core_pago" ("id", "monto", "monto_comision_profesor", "monto_utilidad_asociacion", "motivo_rechazo", "fecha_pago_real", "tipo", "cantidad_clases", "metodo", "comprobante", "estado", "mercado_pago_id", "mercado_pago_status", "fecha_registro", "actividad_id", "alumno_id", "clase_programada_id", "monto_descuento") SELECT "id", "monto", "monto_comision_profesor", "monto_utilidad_asociacion", "motivo_rechazo", "fecha_pago_real", "tipo", "cantidad_clases", "metodo", "comprobante", "estado", "mercado_pago_id", "mercado_pago_status", "fecha_registro", "actividad_id", "alumno_id", "clase_programada_id", '0.00' FROM "core_pago";
DROP TABLE "core_pago";
ALTER TABLE "new__core_pago" RENAME TO "core_pago";
CREATE INDEX "core_pago_actividad_id_a32e0efe" ON "core_pago" ("actividad_id");
CREATE INDEX "core_pago_alumno_id_69d92e10" ON "core_pago" ("alumno_id");
CREATE INDEX "core_pago_clase_programada_id_84239120" ON "core_pago" ("clase_programada_id");
--
-- Add field descuento to pago
--
ALTER TABLE "core_pago" ADD COLUMN "descuento_id" bigint NULL REFERENCES "core_descuento" ("id") DEFERRABLE INITIALLY DEFERRED;
CREATE INDEX "core_pago_descuento_id_04daa727" ON "core_pago" ("descuento_id");
COMMIT;


-- ==========================================
-- ventas.0003
-- ==========================================

BEGIN;
--
-- Add field monto_original to pago
--
CREATE TABLE "new__core_pago" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "monto_original" decimal NOT NULL, "monto" decimal NOT NULL, "monto_comision_profesor" decimal NOT NULL, "monto_utilidad_asociacion" decimal NOT NULL, "motivo_rechazo" text NULL, "fecha_pago_real" date NULL, "tipo" varchar(20) NOT NULL, "cantidad_clases" integer NULL, "metodo" varchar(20) NOT NULL, "comprobante" varchar(100) NULL, "estado" varchar(20) NOT NULL, "mercado_pago_id" varchar(255) NULL, "mercado_pago_status" varchar(50) NULL, "fecha_registro" datetime NOT NULL, "actividad_id" bigint NULL REFERENCES "core_actividad" ("id") DEFERRABLE INITIALLY DEFERRED, "alumno_id" bigint NOT NULL REFERENCES "core_usuario" ("id") DEFERRABLE INITIALLY DEFERRED, "clase_programada_id" bigint NULL REFERENCES "core_cronograma" ("id") DEFERRABLE INITIALLY DEFERRED, "monto_descuento" decimal NOT NULL, "descuento_id" bigint NULL REFERENCES "core_descuento" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_pago" ("id", "monto", "monto_comision_profesor", "monto_utilidad_asociacion", "motivo_rechazo", "fecha_pago_real", "tipo", "cantidad_clases", "metodo", "comprobante", "estado", "mercado_pago_id", "mercado_pago_status", "fecha_registro", "actividad_id", "alumno_id", "clase_programada_id", "monto_descuento", "descuento_id", "monto_original") SELECT "id", "monto", "monto_comision_profesor", "monto_utilidad_asociacion", "motivo_rechazo", "fecha_pago_real", "tipo", "cantidad_clases", "metodo", "comprobante", "estado", "mercado_pago_id", "mercado_pago_status", "fecha_registro", "actividad_id", "alumno_id", "clase_programada_id", "monto_descuento", "descuento_id", '0.00' FROM "core_pago";
DROP TABLE "core_pago";
ALTER TABLE "new__core_pago" RENAME TO "core_pago";
CREATE INDEX "core_pago_actividad_id_a32e0efe" ON "core_pago" ("actividad_id");
CREATE INDEX "core_pago_alumno_id_69d92e10" ON "core_pago" ("alumno_id");
CREATE INDEX "core_pago_clase_programada_id_84239120" ON "core_pago" ("clase_programada_id");
CREATE INDEX "core_pago_descuento_id_04daa727" ON "core_pago" ("descuento_id");
--
-- Alter field descuento on pago
--
-- (no-op)
COMMIT;


-- ==========================================
-- ventas.0004
-- ==========================================

BEGIN;
--
-- Add field monto_reserva to producto
--
CREATE TABLE "new__core_producto" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "monto_reserva" decimal NOT NULL, "nombre" varchar(150) NOT NULL, "descripcion" text NOT NULL, "precio" decimal NOT NULL, "activo" bool NOT NULL, "permite_backorder" bool NOT NULL, "cuotas_maximas" integer NOT NULL, "costo_reposicion" decimal NOT NULL, "porcentaje_comision" decimal NOT NULL, "stock" integer NOT NULL, "foto1" varchar(100) NULL, "foto2" varchar(100) NULL, "foto3" varchar(100) NULL, "foto4" varchar(100) NULL, "foto5" varchar(100) NULL, "categoria_id" bigint NOT NULL REFERENCES "core_categoriaproducto" ("id") DEFERRABLE INITIALLY DEFERRED);
INSERT INTO "new__core_producto" ("id", "nombre", "descripcion", "precio", "activo", "permite_backorder", "cuotas_maximas", "costo_reposicion", "porcentaje_comision", "stock", "foto1", "foto2", "foto3", "foto4", "foto5", "categoria_id", "monto_reserva") SELECT "id", "nombre", "descripcion", "precio", "activo", "permite_backorder", "cuotas_maximas", "costo_reposicion", "porcentaje_comision", "stock", "foto1", "foto2", "foto3", "foto4", "foto5", "categoria_id", '0.00' FROM "core_producto";
DROP TABLE "core_producto";
ALTER TABLE "new__core_producto" RENAME TO "core_producto";
CREATE INDEX "core_producto_categoria_id_65b2d0af" ON "core_producto" ("categoria_id");
--
-- Alter field estado on pedido
--
-- (no-op)
COMMIT;


-- ==========================================
-- ventas.0005
-- ==========================================

BEGIN;
--
-- Add field monto_maximo_descuento to descuento
--
ALTER TABLE "core_descuento" ADD COLUMN "monto_maximo_descuento" decimal NULL;
--
-- Add field monto_minimo_pago to descuento
--
CREATE TABLE "new__core_descuento" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "nombre" varchar(150) NOT NULL, "descripcion" text NOT NULL, "tipo" varchar(20) NOT NULL, "valor" decimal NOT NULL, "codigo" varchar(50) NOT NULL, "activo" bool NOT NULL, "usos_maximos" integer unsigned NULL CHECK ("usos_maximos" >= 0), "usos_actuales" integer unsigned NOT NULL CHECK ("usos_actuales" >= 0), "fecha_vencimiento" date NULL, "aplicable_a" varchar(20) NOT NULL, "monto_maximo_descuento" decimal NULL, "monto_minimo_pago" decimal NOT NULL);
INSERT INTO "new__core_descuento" ("id", "nombre", "descripcion", "tipo", "valor", "codigo", "activo", "usos_maximos", "usos_actuales", "fecha_vencimiento", "aplicable_a", "monto_maximo_descuento", "monto_minimo_pago") SELECT "id", "nombre", "descripcion", "tipo", "valor", "codigo", "activo", "usos_maximos", "usos_actuales", "fecha_vencimiento", "aplicable_a", "monto_maximo_descuento", '0.00' FROM "core_descuento";
DROP TABLE "core_descuento";
ALTER TABLE "new__core_descuento" RENAME TO "core_descuento";
--
-- Create constraint unique_active_discount_code on model descuento
--
CREATE UNIQUE INDEX "unique_active_discount_code" ON "core_descuento" ("codigo") WHERE "activo";
COMMIT;


-- ==========================================
-- ventas.0006
-- ==========================================

BEGIN;
--
-- Alter field codigo on descuento
--
CREATE TABLE "new__core_descuento" ("id" integer NOT NULL PRIMARY KEY AUTOINCREMENT, "codigo" varchar(50) NOT NULL, "nombre" varchar(150) NOT NULL, "descripcion" text NOT NULL, "tipo" varchar(20) NOT NULL, "valor" decimal NOT NULL, "activo" bool NOT NULL, "usos_maximos" integer unsigned NULL CHECK ("usos_maximos" >= 0), "usos_actuales" integer unsigned NOT NULL CHECK ("usos_actuales" >= 0), "fecha_vencimiento" date NULL, "aplicable_a" varchar(20) NOT NULL, "monto_maximo_descuento" decimal NULL, "monto_minimo_pago" decimal NOT NULL);
INSERT INTO "new__core_descuento" ("id", "nombre", "descripcion", "tipo", "valor", "activo", "usos_maximos", "usos_actuales", "fecha_vencimiento", "aplicable_a", "monto_maximo_descuento", "monto_minimo_pago", "codigo") SELECT "id", "nombre", "descripcion", "tipo", "valor", "activo", "usos_maximos", "usos_actuales", "fecha_vencimiento", "aplicable_a", "monto_maximo_descuento", "monto_minimo_pago", "codigo" FROM "core_descuento";
DROP TABLE "core_descuento";
ALTER TABLE "new__core_descuento" RENAME TO "core_descuento";
CREATE UNIQUE INDEX "unique_active_discount_code" ON "core_descuento" ("codigo") WHERE "activo";
CREATE INDEX "core_descuento_codigo_b27d2f91" ON "core_descuento" ("codigo");
--
-- Alter field alumno on pago
--
-- (no-op)
--
-- Alter field alumno on pedido
--
-- (no-op)
COMMIT;
