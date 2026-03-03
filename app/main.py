from fastapi import FastAPI, Depends
from app.router.app_router import AppRouter

class Application:
    def __init__(self):
        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self):
        self.app.include_router(AppRouter().router)

app = Application().app

@app.get("/")
async def root():
    return {"message":"Virus Total Data Pipeline"}

# app.include_router(router)