<template>
  <div>
    <b-table
        :data="sources"
        :loading="loading"
    >
      <b-table-column field="name" label="Name" v-slot="props">
        <router-link to="">{{ props.row.name }}</router-link>
      </b-table-column>

      <b-table-column field="active" label="Enabled" v-slot="props" centered>
        <b-button icon-left="check"
                  icon-pack="fas"
                  :type="props.row.active ? 'is-success' : 'is-dark'"
                  class="is-inverted is-shadowless"
                  style="background: none"
                  @click="toggleActive(props.row)"
        />

      </b-table-column>

      <b-table-column v-slot="props">
        <b-button @click="syncNow(props.row)" label="Sync now" type="is-primary" class="is-pulled-right"/>
      </b-table-column>

    </b-table>

  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Dashboard',

  data() {
    return {
      loading: false,
      sources: []
    }
  },

  mounted() {
    this.getDataSources()
  },

  methods: {
    toggleActive(row) {
      alert(row.id)
    },

    syncNow(row) {
      alert(row.id)
    },

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
