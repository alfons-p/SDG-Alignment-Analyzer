// Whether a bulk upload batch is currently running. Read by the axios 401
// interceptor so it never hard-navigates to /login mid-batch (which would
// silently kill the batch). Module-level singleton, set by UploadQueue.
let active = false
export const setBatchActive = (v: boolean) => {
  active = v
}
export const isBatchActive = () => active
