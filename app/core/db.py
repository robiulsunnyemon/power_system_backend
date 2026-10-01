from prisma import Prisma

db = Prisma()

async def ensure_allowed_locations_table():
    try:
        await db.execute_raw('''
            CREATE TABLE IF NOT EXISTS "allowed_locations" (
                "id" SERIAL NOT NULL,
                "name" TEXT NOT NULL,
                "state" TEXT NOT NULL DEFAULT 'WA',
                "country" TEXT NOT NULL DEFAULT 'Australia',
                "latitude" DOUBLE PRECISION NOT NULL,
                "longitude" DOUBLE PRECISION NOT NULL,
                "radiusKm" DOUBLE PRECISION NOT NULL DEFAULT 60.0,
                "isActive" BOOLEAN NOT NULL DEFAULT true,
                "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT "allowed_locations_pkey" PRIMARY KEY ("id")
            );
        ''')
        await db.execute_raw('''
            CREATE UNIQUE INDEX IF NOT EXISTS "allowed_locations_name_key" ON "allowed_locations"("name");
        ''')
        # Check if Perth exists, if not insert it
        count = await db.query_raw('''
            SELECT count(*)::int as c FROM "allowed_locations";
        ''')
        c = 0
        if count and len(count) > 0:
            c = count[0].get("c", 0)
        if c == 0:
            await db.execute_raw('''
                INSERT INTO "allowed_locations" ("name", "state", "country", "latitude", "longitude", "radiusKm", "isActive", "createdAt", "updatedAt")
                VALUES ('Perth', 'WA', 'Australia', -31.9505, 115.8605, 60.0, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT ("name") DO NOTHING;
            ''')
            print("Seeded initial allowed location: Perth, WA, Australia")
    except Exception as e:
        print(f"Notice on ensure_allowed_locations_table: {e}")

async def connect_db():
    if not db.is_connected():
        await db.connect()
        await ensure_allowed_locations_table()

async def disconnect_db():
    if db.is_connected():
        await db.disconnect()
