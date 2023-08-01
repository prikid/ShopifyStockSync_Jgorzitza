import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import Buefy from 'buefy'
import 'buefy/dist/buefy.css'
import axios from 'axios'

axios.defaults.baseURL = process.env.VUE_APP_BACKEND_HOST

Vue.config.productionTip = false;
Vue.use(Buefy);

// Vue.component('vue-csv-import', VueCsvImport);

// Vue.component('my-component-name', { /* ... */ })

store.dispatch("initialize")

new Vue({
    store,
    router,
    render: h => h(App),
}).$mount('#app')


