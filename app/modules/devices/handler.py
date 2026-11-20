from fastapi import APIRouter, Request, Body
from app.engine import evaluate
from app.web import render
router=APIRouter()
@router.get('/devices')
def page(request:Request):
    return render(request,'devices')
@router.post('/api/devices')
def calculate(payload:dict=Body(default={})):
    return evaluate(payload,until=2)
