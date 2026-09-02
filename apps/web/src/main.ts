import { createApp } from "vue";
import { FrappeUI } from "frappe-ui";

import App from "./App.vue";
import router from "./router";
import "./app/styles.css";

createApp(App).use(router).use(FrappeUI).mount("#app");
