# Project Requirements & Workflow

## Objective

Single-owner catering platform. Customers interact via **WhatsApp bot**. Owner manages everything from the **React dashboard**.

## WhatsApp Customer Flow

1. Customer sends a message
2. Bot collects: name, phone, event type, date, location, guest count, callback time
3. Bot shows **dish categories** → customer selects types needed
4. Bot shows **dishes per category** → customer selects items
5. Bot asks for **customizations** (No Milk, No Onion, Less Spice, etc.)
6. Enquiry saved with full menu selection
7. Owner receives instant WhatsApp notification
8. Reminder sent 15–20 minutes before callback time
9. Enquiry appears on dashboard **Enquiries** page

## Dish Categories

South Indian · North Indian · Chinese · Snacks · Desserts · Beverages

## Customizations

No Milk · No Onion · No Garlic · Less Spice · Less Sweet · Extra Vegetables

## Owner Dashboard

- Live enquiries with dishes and customizations
- Update enquiry status (NEW → CONTACTED → CONVERTED → CLOSED)
- Menu management view
- AI assistant for queries
- Bot tester for development

## Planned Modules

Orders · Invoices (Kitchen/Billing copy) · Vendors · Workers · Expenses · Profit analytics

## Folder Structure

```
Kannans/
├── whatsapp/     # FastAPI backend
├── website/      # React dashboard
├── shared/       # Prisma reference
└── docs/         # Documentation
```
