# Step 3 — MongoDB Atlas Setup (Free Tier)

## A. Create Your Free Cluster

1. Go to https://cloud.mongodb.com and sign in (or create a free account)
2. Click **"Build a Database"**
3. Choose **M0 FREE** tier
4. Select **AWS** → **us-east-1** (closest to Cloud Run us-central1)
5. Name it: `retailpulse-cluster`
6. Click **"Create"**

## B. Create a Database User

1. In the left sidebar → **Database Access** → **Add New Database User**
2. Username: `retailpulse`
3. Password: generate a strong one and **save it**
4. Role: **Atlas Admin** (or Read and Write to Any Database)
5. Click **Add User**

## C. Allow Network Access

1. Left sidebar → **Network Access** → **Add IP Address**
2. Click **"Allow Access from Anywhere"** → `0.0.0.0/0`
   *(Required for Cloud Run — Cloud Run IPs are dynamic)*
3. Click **Confirm**

## D. Get Your Connection String

1. Left sidebar → **Database** → click **Connect** on your cluster
2. Choose **"Drivers"**
3. Driver: **Python**, Version: **3.12 or later**
4. Copy the connection string — it looks like:
   ```
   mongodb+srv://retailpulse:<password>@retailpulse-cluster.xxxxx.mongodb.net/
   ```
5. Replace `<password>` with your actual password
6. Add the database name at the end:
   ```
   mongodb+srv://retailpulse:YOURPASSWORD@retailpulse-cluster.xxxxx.mongodb.net/retailpulse
   ```
7. **Save this** — it's your `MONGODB_URI`

## E. Seed the Database

Once you have the URI, run from the project folder:
```bash
# Install pymongo first
pip install pymongo python-dotenv

# Set the URI temporarily
set MONGODB_URI=mongodb+srv://retailpulse:YOURPASSWORD@retailpulse-cluster.xxxxx.mongodb.net/retailpulse

# Seed 90 days of demo data
python scripts/seed_data.py
```

You should see:
```
✅ Connected to MongoDB Atlas
✅ Seeded 20 tenants
✅ Seeded 1800 revenue records
✅ Seeded 94640 footfall records
✅ Seeded 3 promotions
✅ Seeded 3 alerts
✅ Seeded 1 reports
```

## F. Enable Vector Search Index (Bonus — impresses MongoDB judges)

1. In Atlas UI → your cluster → **Search** tab → **Create Search Index**
2. Choose **Atlas Vector Search** → **JSON Editor**
3. Database: `retailpulse`, Collection: `reports`
4. Paste this config:
```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 1536,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "type"
    }
  ]
}
```
5. Name it `reports_vector_index` → **Create**

## G. Get Atlas API Credentials (Optional — enables Performance Advisor)

1. Atlas UI → top-left org menu → **Organization Settings**
2. Left sidebar → **Access Manager** → **API Keys** → **Create API Key**
3. Description: `RetailPulse MCP`
4. Permission: **Organization Member**
5. Copy the **Client ID** and **Client Secret**
6. Add these to your `.env`:
   ```
   MDB_ATLAS_CLIENT_ID=your_client_id
   MDB_ATLAS_CLIENT_SECRET=your_client_secret
   ```
