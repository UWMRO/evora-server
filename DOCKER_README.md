# How to use Docker for this

You will need the following structure:

```bash
root/
├─ evora-server/
├─ evora-client/
├─ docker-compose.yml
```

The `docker-compose.yml` is a new file that is attached below:

```yaml
version: '3.8'

services:
  evora-server:
    build:
      context: ./evora-server
    ports:
      - "3000:3000"
    volumes:
      - ./evora-server:/usr/src/app
    command: python app.py  # Start the Flask app
    environment:
      - FLASK_RUN_HOST=0.0.0.0  # Bind to all interfaces for external access
      - FLASK_ENV=development   # Optional: Enables Flask debug mode for development

  evora-client:
    build:
      context: ./evora-client
    ports:
      - "3001:3001"
    volumes:
      - ./evora-client:/usr/src/app
      - /usr/src/app/node_modules  # Add this to map node_modules correctly

    command: npm start  # Start the React app
    environment:
      - PORT=3001         # Set the port for the React app
    depends_on:
      - evora-server
```

When you have this structure, go to the root directory and use the following command in the console (install Docker first):
`docker compose up --build`
which will build the container and run it. Then you can access the web app at

`http://127.0.0.1:3001`.

Note: When you React or Flask files, you do NOT need to rebuild the container. It will be automatically updated without you having to restart anything.