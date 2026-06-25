-- SRIVATSANKA / Kannans — Supabase (PostgreSQL) schema
-- Run in Supabase → SQL Editor → New query → Run
--
-- NOTE: If your API is already deployed with DATABASE_URL set, tables are
-- created automatically on startup. Only run this if you want to set up
-- tables manually before the first API deploy.

-- Enums (names match SQLAlchemy defaults)
DO $$ BEGIN
  CREATE TYPE enquirystatus AS ENUM (
    'NEW', 'SEEN', 'CONTACTED', 'CONVERTED', 'NOT_CONVERTED'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE notificationtype AS ENUM ('NEW_ENQUIRY', 'CALLBACK_REMINDER');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
  CREATE TYPE dishcategory AS ENUM (
    'BREAKFAST', 'LUNCH', 'DINNER', 'RECEPTION_DINNER',
    'COFFEE', 'TEA', 'JUICE', 'DESSERT', 'SNACKS'
  );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Core tables
CREATE TABLE IF NOT EXISTS "Enquiry" (
  id VARCHAR PRIMARY KEY,
  "customerName" VARCHAR NOT NULL,
  "phoneNumber" VARCHAR NOT NULL,
  "eventType" VARCHAR NOT NULL,
  "eventDate" TIMESTAMP NOT NULL,
  "eventLocation" VARCHAR NOT NULL,
  "guestCount" INTEGER NOT NULL,
  "preferredCallbackAt" TIMESTAMP NOT NULL,
  status enquirystatus NOT NULL DEFAULT 'NEW',
  "ownerViewedAt" TIMESTAMP,
  "reminderSent" BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW(),
  "updatedAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "Dish" (
  id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  category dishcategory NOT NULL,
  price DOUBLE PRECISION NOT NULL DEFAULT 0,
  description TEXT,
  "isActive" BOOLEAN NOT NULL DEFAULT TRUE,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "EnquiryDish" (
  id VARCHAR PRIMARY KEY,
  "enquiryId" VARCHAR NOT NULL REFERENCES "Enquiry"(id) ON DELETE CASCADE,
  "dishId" VARCHAR REFERENCES "Dish"(id),
  "dishName" VARCHAR NOT NULL,
  category VARCHAR NOT NULL,
  customizations TEXT,
  notes TEXT,
  quantity DOUBLE PRECISION NOT NULL DEFAULT 1,
  "quantityUnit" VARCHAR NOT NULL DEFAULT 'pcs',
  "unitPrice" DOUBLE PRECISION,
  served BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS "InvoiceUpload" (
  id VARCHAR PRIMARY KEY,
  "enquiryId" VARCHAR REFERENCES "Enquiry"(id) ON DELETE SET NULL,
  "docType" VARCHAR NOT NULL,
  "fileName" VARCHAR NOT NULL,
  "filePath" VARCHAR NOT NULL,
  amount DOUBLE PRECISION,
  notes TEXT,
  purpose VARCHAR,
  "expenseDate" TIMESTAMP,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "Notification" (
  id VARCHAR PRIMARY KEY,
  type notificationtype NOT NULL,
  title VARCHAR NOT NULL,
  message VARCHAR NOT NULL,
  read BOOLEAN NOT NULL DEFAULT FALSE,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "WhatsappChatMessage" (
  id VARCHAR PRIMARY KEY,
  "phoneNumber" VARCHAR NOT NULL,
  role VARCHAR NOT NULL,
  body TEXT NOT NULL,
  "mediaJson" TEXT,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_whatsappchatmessage_phonenumber
  ON "WhatsappChatMessage" ("phoneNumber");
CREATE INDEX IF NOT EXISTS ix_whatsappchatmessage_createdat
  ON "WhatsappChatMessage" ("createdAt");

CREATE TABLE IF NOT EXISTS "WhatsappChatState" (
  "phoneNumber" VARCHAR PRIMARY KEY,
  "botPaused" BOOLEAN NOT NULL DEFAULT FALSE,
  "pausedAt" TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "Vendor" (
  id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  "businessName" VARCHAR,
  "phoneNumber" VARCHAR NOT NULL,
  category VARCHAR NOT NULL,
  notes TEXT,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "Worker" (
  id VARCHAR PRIMARY KEY,
  name VARCHAR NOT NULL,
  "phoneNumber" VARCHAR NOT NULL,
  role VARCHAR NOT NULL,
  "dailyWage" DOUBLE PRECISION NOT NULL DEFAULT 0,
  "isLead" BOOLEAN NOT NULL DEFAULT FALSE,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "WorkerAssignment" (
  id VARCHAR PRIMARY KEY,
  "workerId" VARCHAR NOT NULL REFERENCES "Worker"(id) ON DELETE CASCADE,
  "enquiryId" VARCHAR REFERENCES "Enquiry"(id) ON DELETE SET NULL,
  "dutyDate" TIMESTAMP NOT NULL,
  "dutyType" VARCHAR NOT NULL,
  wage DOUBLE PRECISION NOT NULL DEFAULT 0,
  "paymentCompleted" BOOLEAN NOT NULL DEFAULT FALSE,
  notes TEXT,
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS "Expense" (
  id VARCHAR PRIMARY KEY,
  category VARCHAR NOT NULL,
  amount DOUBLE PRECISION NOT NULL,
  description TEXT,
  "expenseDate" TIMESTAMP NOT NULL DEFAULT NOW(),
  "createdAt" TIMESTAMP NOT NULL DEFAULT NOW()
);
