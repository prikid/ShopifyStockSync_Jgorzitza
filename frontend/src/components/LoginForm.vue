<template>
  <form @submit.prevent="submitLogin">
    <div class="modal-card" style="width: auto">
      <header class="modal-card-head">
        <p class="modal-card-title">Login</p>
        <button v-if="isModalMode" type="button" class="delete" @click="$emit('close')"/>
      </header>
      <section class="modal-card-body">
        <b-field label="Email">
          <b-input type="email" v-model="email" placeholder="Your email" required></b-input>
        </b-field>

        <b-field label="Password">
          <b-input type="password" v-model="password" password-reveal placeholder="Your password" required></b-input>
        </b-field>

        <!--        <b-checkbox>Remember me</b-checkbox>-->
      </section>
      <footer class="modal-card-foot">
        <b-button v-if="isModalMode" label="Close" @click="$emit('close')"/>
        <b-button native-type="submit" label="Login" type="is-primary"/>
      </footer>
    </div>
  </form>
</template>

<script>
import axios from 'axios'
export default {
  name: "LoginForm",

  props: {
    isModalMode: false
  },

  data() {
    return {
      email: '',
      password: ''
    }
  },

  methods: {
    async submitLogin() {
      const formData = {
        email: this.email,
        password: this.password
      }

      await axios.post("/api/user/token/", formData)
          .then(response => {
            const token = response.data.token;
            this.$store.commit('setToken', token);
            axios.defaults.headers.common['Authorization'] = 'Token ' + token;
            localStorage.setItem('token', token);
            this.$emit('authenticated')
          })
          .catch(e => {
            this.$emit('authentication_error', e)
          })
    }
  }
}
</script>

<style scoped>

</style>