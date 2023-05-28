<template>
  <section class="hero">
    <div class="hero-body">

    </div>
  </section>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Dashboard',

  data() {
    return {
      sources:[]
    }
  },

  methods: {
    async getDataSources() {
      this.loading = true
      axios.get('/api/sources/')
          .then(({data}) => {
            this.sources = data
            console.log(this.sources);
            this.loading = false
          })
          .catch((error) => {
            this.sources = []
            this.loading = false
            throw error
          })
    }
  }
}

</script>
