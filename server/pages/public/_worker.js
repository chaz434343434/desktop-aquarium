// The same server, reachable at desktop-aquarium.pages.dev (some networks block every workers.dev address).
// Both addresses share one database. The workers.dev copy stays because only it can run the weekly cleanup.
export { default } from "../../src/worker.js";
