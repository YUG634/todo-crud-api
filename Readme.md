# To-Do CRUD API

An in-memory RESTful API built with FastAPI demonstrating foundational CRUD operations, status code rigor, request validation, and OpenAPI/Swagger documentation.

## Running Locally

```bash
# 1. Clone & setup virtual environment
git clone [https://github.com/](https://github.com/)<your-username>/todo-crud-api.git
cd todo-crud-api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn main:app --reload --port 8000