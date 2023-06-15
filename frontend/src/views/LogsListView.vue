<template>
  <div class="container">
    <b-table :data="logGroups" :loading="loading">
      <b-table-column field="id" label="ID" v-slot="props">
        {{ props.row.gid }}
      </b-table-column>

      <b-table-column field="time" label="Time" v-slot="props">
        {{ formatTime(props.row.time) }}
      </b-table-column>

      <b-table-column field="source" label="Source" v-slot="props">
        {{ props.row.source }}
      </b-table-column>

      <b-table-column v-slot="props">
        <b-button @click="downloadLogCsv(props.row)" label="Download CSV"
                  type="is-secondary" size="is-small" class="is-pulled-right"/>
      </b-table-column>

    </b-table>
  </div>

</template>

<script>
import axios from "axios";
import DownloadFileMixin from "@/mixins/DownloadFileMixin.vue";

export default {
  name: "LogsListView",
  mixins: [DownloadFileMixin],

  data() {
    return {
      logGroups: [],
      loading: false
    }
  },

  mounted() {
    this.getLogGroups()
  },

  methods: {
    downloadLogCsv(row) {
      const url = `/api/logs/download-csv/${row.gid}`
      this.downloadFile(url)
    },

    formatTime(timeString) {
      // Convert the string to a Date object
      const date = new Date(timeString);

      return date.toLocaleString('default', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })

    },

    async getLogGroups() {
      this.loading = true
      axios.get('/api/logs/groups')
          .then(({data}) => {
            this.logGroups = data
            this.loading = false
          })
          .catch((error) => {
            this.logGroups = []
            this.loading = false
            throw error
          })
    }
  }
}
</script>

<style scoped>

</style>