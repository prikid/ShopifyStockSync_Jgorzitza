import Vue from 'vue'
import Vuex from 'vuex'

Vue.use(Vuex)

export default new Vuex.Store({
    state: {
        isAuthenticated: false,
        token: ''
    },
    getters: {},
    mutations: {
        initialize(state) {
            const token = localStorage.getItem('token')
            if (token) {
                state.token = token
                state.isAuthenticated = true
            } else {
                state.token = ''
                state.isAuthenticated = false
            }
        },

        setToken(state, token) {
            state.token = token;
            state.isAuthenticated = true;
        },
        removeToken(state) {
            state.token = '';
            state.isAuthenticated = false;
        }
    },
    actions: {},
    modules: {}
})
