module.exports = function(grunt) {

  grunt.initConfig({
    mustache_render: {
      all: {
        files: [
          {
            data: "data.json",
            template: "layout.mustache",
            dest: "index.html"
          }
        ]
      }
    },
    sass: {
      dist: {
        files: {
          'css/main.css': 'scss/main.scss'
        }
      }
    },
    watch: {
      template: {
        files: ["data.json", "layout.mustache"],
        tasks: ['mustache_render'],
        options: {
          spawn: true
        }
      },
      scss: {
        files: ['scss/*.scss'],
        tasks: ['sass'],
        options: {
          spawn: true
        }
      }
    }
  });

  grunt.loadNpmTasks('grunt-mustache-render');
  grunt.loadNpmTasks('grunt-contrib-watch');
  grunt.loadNpmTasks('grunt-sass');

  grunt.registerTask('default', ['mustache_render', 'sass']);
};
