from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"status": "Clinic AI Assistant running"}