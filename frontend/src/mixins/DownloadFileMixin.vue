<script>
import axios from "axios";

export default {
  name: "DownloadFileMixin",

  methods: {
    downloadFile(url) {
      axios.get(url, {responseType: 'blob'})
          .then(response => {
            const headerLine = response.headers['content-disposition'];
            const filename = headerLine.substring(headerLine.indexOf('"') + 1, headerLine.lastIndexOf('"'));

            const file = new Blob([response.data], {type: response.headers['content-type']});
            const url = window.URL.createObjectURL(file);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', filename);
            document.body.appendChild(link);

            // Trigger the download
            link.click();

            // Clean up
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
          })
    },
  }
}
</script>
