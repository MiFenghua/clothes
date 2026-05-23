import { config } from "./config.js";
import { createApp } from "./app.js";

const app = createApp();

app.listen(config.port, () => {
  console.log(`clothes-api listening on ${config.publicBaseUrl}`);
});
