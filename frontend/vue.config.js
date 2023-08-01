const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  chainWebpack: config => {
    config.resolve.alias.set('path', require.resolve('path-browserify'));

    config.plugin('html').tap(args => {
      args[0].title = 'One Guy Garage Store Sync'; // The title for the generated HTML page
      return args;
    });
  }
})